"""Generate per-character Breakdown lines from CC-CEDICT.

Follows the word-deck convention:
  `char (gloss) char (gloss) …`
  ordered by first appearance in the Hanzi line, deduped, lowercase, 1-3 words.

The auto-picked gloss is naive (first surviving definition after filtering
out surname / variant / pronunciation notes). For polysemous chars in a
song's context the user is expected to hand-edit the output before
import.
"""
from __future__ import annotations
import argparse, re
from pathlib import Path


CEDICT_PATH = Path(__file__).parent / "cache" / "cedict_ts.u8"


# CJK ideograph range (BMP). Extension A is in 0x3400-0x4DBF; songs rarely
# use those, but cheap to include.
CJK_RE = re.compile(r"[㐀-鿿]")

# Definitions we never want to use as the primary gloss.
SKIP_PREFIXES = (
    "surname ",
    "see ",
    "variant of ",
    "old variant of ",
    "japanese variant of ",
    "taiwan pr. ",
    "taiwan pr ",
    "cl:",
    "abbr. for ",
    "used in ",
    "used as ",
    "-ly",
    "structural particle",
    "modal particle",
    "grammatical particle",
    "interjection",
    "phonetic",
    "japanese surname",
)

# Defs we drop when their content suggests they're meta-info rather than
# a learner-facing gloss (e.g. radical descriptions).
SKIP_SUBSTRINGS = (
    "kangxi radical",
    " radical ",
    " radical,",
    " radical.",
    " radical;",
    "radical in chinese",
    '"',  # CEDICT quotes radical/component descriptions
)

# Strip these leading particles to get a punchier gloss.
LEADING_STRIP = (
    "to be ",
    "to ",
    "a ",
    "an ",
    "the ",
)

# Leading parenthetical labels we want to strip without nuking the gloss
# (e.g. "(bound form) feelings; emotion" -> "feelings; emotion").
PAREN_LABEL_RE = re.compile(r"^\s*[\(（][^)）]{0,40}[\)）]\s*")


# Manual overrides for common chars where CEDICT's first usable def is
# pedagogically off for song-deck context. Add sparingly.
CHAR_OVERRIDES = {
    "天": "sky",
    "中": "middle",
    "地": "earth",
    "所": "place",
    "云": "cloud",
    "广": "wide",
    "原": "plain",
    "过": "past-particle",
    "了": "particle",
    "向": "toward",
    "之": "possessive",
    "啸": "howl",
    "片": "stretch",
    "时": "time",
    "阔": "wide",
    "就": "just",
    "伊": "that",
    "丈": "ten feet",
    "层": "layer",
    "真": "true",
    "情": "feeling",
    "像": "like",
    "总": "always",
    "最": "most",
    "看": "see",
    "在": "at",
    "出": "out",
    "光": "light",
    "放": "release",
    "傲": "proud",
    "立": "stand",
    "长": "long",
    "留": "stay",
    "阳": "sun",
    "阔": "broad",
    "剪": "cut",
    "无": "without",
    "没": "not",
    "为": "for",
    "候": "wait",
    # Time / daily-life
    "点": "o'clock",
    "班": "shift",
    "楼": "floor",
    "然": "thus",
    "后": "after",
    "子": "suffix",
    "才": "only",
    "理": "reason",
    "由": "cause",
    "发": "send",
    # GANMA-prevalent
    "干": "do",
    "嘛": "(question)",
    "周": "week",
    "着": "(state-particle)",
    "钟": "clock",
    "派": "send",
    "装": "pretend",
    "便": "convenient",
    "几": "how-many",
    "管": "manage",
    "呢": "(question)",
    "谓": "call",
    "说": "say",
    "疼": "hurt",
    # Meditation line
    "让": "let",
    "们": "(plural)",
    "首": "first",
    "先": "before",
    "将": "(will)",
    "注": "pour",
    "意": "meaning",
    "力": "force",
    "缓": "slow",
    "慢": "slow",
    "呼": "exhale",
    "吸": "inhale",
    "气": "air",
    "厘": "centi",
    "醉": "drunk",
    "喝": "drink",
    "夜": "night",
    "眼": "eye",
    "睛": "eye",
    "连": "even",
    "秒": "second",
    "受": "endure",
}


def load_cedict(path: Path = CEDICT_PATH) -> dict[str, list[str]]:
    """Return {simplified -> [definitions]}.

    - Aggregates defs across ALL traditional variants that share the same
      simplified form (e.g. 嘯/啸, 廣/广).
    - Skips entries whose pinyin starts with an uppercase letter — those
      are proper nouns (surnames, place names) and almost never the gloss
      we want first.
    """
    out: dict[str, list[str]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line or line.startswith("#"):
                continue
            # format: trad simp [pinyin] /def1/def2/.../
            try:
                _trad, rest = line.split(" ", 1)
                simp, rest = rest.split(" ", 1)
                pinyin, defs_part = rest.split("] ", 1)
                pinyin = pinyin.lstrip("[")
                defs = [d for d in defs_part.strip().strip("/").split("/") if d]
            except ValueError:
                continue
            # Drop proper-noun entries (first letter of first syllable uppercase).
            if pinyin and pinyin[0].isupper():
                continue
            out.setdefault(simp, []).extend(defs)
    return out


def pick_gloss(defs: list[str]) -> str | None:
    """Return a short, learner-friendly gloss, or None if nothing usable."""
    for raw in defs:
        d = raw.strip()
        if not d:
            continue
        # Skip meta-defs that aren't useful glosses (radical descriptions etc.)
        d_low = d.lower()
        if any(s in d_low for s in SKIP_SUBSTRINGS):
            continue
        # Strip a leading parenthetical label like "(bound form) " or
        # "(literary) " — but only one layer; don't eat the whole gloss.
        d = PAREN_LABEL_RE.sub("", d, count=1).strip()
        if not d:
            continue
        if any(d.lower().startswith(p) for p in SKIP_PREFIXES):
            continue
        # Drop ALL parentheticals (not just trailing). Defs like "to float
        # (in the air); to flutter" have parens mid-string; if we only strip
        # at end the inner paren survives and the gloss ends up ugly.
        d = re.sub(r"\s*[\(（][^)）]*[\)）]", "", d).strip(" ,.;:")
        # Take only the first alt-sense (defs sometimes pack multiple via ;).
        d = re.split(r"[;,]", d, maxsplit=1)[0].strip()
        if not d:
            continue
        for lead in LEADING_STRIP:
            if d.lower().startswith(lead):
                d = d[len(lead):]
                break
        d = d.strip()
        if not d:
            continue
        return d.lower()
    return None


def breakdown_for_line(line: str, cedict: dict[str, list[str]]) -> str:
    """Per-char Breakdown string for one Hanzi line."""
    seen: set[str] = set()
    parts: list[str] = []
    missing: list[str] = []
    for ch in line:
        if not CJK_RE.match(ch) or ch in seen:
            continue
        seen.add(ch)
        if ch in CHAR_OVERRIDES:
            parts.append(f"{ch} ({CHAR_OVERRIDES[ch]})")
            continue
        defs = cedict.get(ch)
        if not defs:
            missing.append(ch)
            parts.append(f"{ch} (?)")
            continue
        gloss = pick_gloss(defs)
        if gloss is None:
            missing.append(ch)
        parts.append(f"{ch} ({gloss or '?'})")
    if missing:
        print(f"  warn: no usable gloss for {missing}")
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lyrics", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--cedict", type=Path, default=CEDICT_PATH)
    args = ap.parse_args()
    cedict = load_cedict(args.cedict)
    print(f"loaded {len(cedict)} CEDICT entries")
    lines = [ln.strip() for ln in args.lyrics.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out_lines: list[str] = []
    for i, line in enumerate(lines, 1):
        bd = breakdown_for_line(line, cedict)
        out_lines.append(bd)
        print(f"  {i:02d}: {len(bd)} chars of breakdown")
    args.out.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"wrote {len(out_lines)} breakdowns -> {args.out}")


if __name__ == "__main__":
    main()
