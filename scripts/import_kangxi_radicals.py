#!/usr/bin/env python3
"""Generate Chinese_Kangxi_Radicals.tsv from the seed Radicals.txt source.

One-shot, NOT idempotent. Overwrites on every run.

Source: hand-curated 6-column TSV with mixed conventions —
- col 0: traditional radical, optionally with variants in parens `心 (忄,⺗)`
- col 1: simplified variant (single CJK char), OR a pronunciation note
  `(pr.chǎng)`, OR empty
- col 2: pinyin, occasionally with alternate readings `yòng (shuǎi)`
- col 3: English meaning
- col 4: comma-separated curated example characters
- col 5: tags (mostly empty)

This script normalizes that into the 15-col radicals deck schema, splitting
variants into Variant1 / Variant2 / ReferenceVariants slots so Anki can
generate one card per primary variant.

Usage:
  python scripts/import_kangxi_radicals.py [--source PATH]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.parse
from pathlib import Path

from common import HAN_RE, REPO_ROOT
from radicals_common import (
    RADICALS_DECK_PATH,
    RADICALS_HEADER,
)

DEFAULT_SOURCE = Path(
    r"C:\Users\hissa\OneDrive\Työpöytä\Radicals.txt"
)
HANZICRAFT_URL = "https://hanzicraft.com/dashboard/character/{}"

# ---------------------------------------------------------------------------
# Pinyin tonemark → numeric conversion (reverse of the table used in
# import_phonetic_components). Needed to build the unique Key column.
# ---------------------------------------------------------------------------

_TONE_MAP: dict[str, tuple[str, int]] = {}
for base, marks in [
    ("a", ["ā", "á", "ǎ", "à"]),
    ("e", ["ē", "é", "ě", "è"]),
    ("i", ["ī", "í", "ǐ", "ì"]),
    ("o", ["ō", "ó", "ǒ", "ò"]),
    ("u", ["ū", "ú", "ǔ", "ù"]),
    ("ü", ["ǖ", "ǘ", "ǚ", "ǜ"]),
]:
    for i, m in enumerate(marks, start=1):
        _TONE_MAP[m] = (base, i)


def pinyin_marks_to_numeric(syllable: str) -> str:
    """`gǒng` → `gong3`, `yòng` → `yong4`, `tóu` → `tou2`. Tone 5 = no digit."""
    if not syllable:
        return ""
    s = syllable.strip().lower()
    base_chars: list[str] = []
    tone = 0
    for ch in s:
        if ch in _TONE_MAP:
            base, t = _TONE_MAP[ch]
            base_chars.append(base)
            tone = t
        else:
            base_chars.append(ch)
    out = "".join(base_chars)
    return f"{out}{tone}" if tone else out


# ---------------------------------------------------------------------------
# Variant ordering overrides. Source often lists variants in arbitrary order;
# pick the most-used-in-modern-writing one as Variant1. Keys are the canonical
# simplified radical.
# ---------------------------------------------------------------------------

VARIANT_OVERRIDES: dict[str, list[str]] = {
    # 水: source has 氺,氵 but 氵 is by far the more common positional form
    "水": ["氵", "氺"],
    # 心: 忄 (left) is much more common than ⺗ (bottom)
    "心": ["忄", "⺗"],
    # 火: 灬 (bottom) is the standard reduction
    "火": ["灬"],
    # 玉: 王 (in compound chars) is the productive form, 玊 is rare
    "玉": ["王", "玊", "⺩"],
    # 人: 亻 (left) much more common than 𠆢 (top)
    "人": ["亻", "𠆢"],
    # 网: 罒 is by far the dominant variant; rest are archaic
    "网": ["罒"],
    "网繁": ["罒"],
    # 手: 扌 (left) is the productive form
    "手": ["扌", "龵"],
    # 辵: 辶 is the standard simplified form
    "辵": ["辶", "⻌", "⻍"],
    # 邑: 阝 on the RIGHT signals 'city/state' — primary positional form
    "邑": ["阝", "⻏", "⻖"],
    # 阜: 阝 on the LEFT signals 'mound/hill' — same glyph, different role
    "阜": ["阝"],
    # 衣: 衤 (left) is the positional form
    "衣": ["衤"],
    # 刀: 刂 (right) is the positional form
    "刀": ["刂"],
    # 言: 讠 (simplified-left) is dominant in modern usage
    "言": ["讠", "訁"],
    # 食: 饣 (simplified-left) is dominant; 飠 is traditional
    "食": ["饣", "飠"],
    # 金: 钅 (simplified-left) is dominant; 釒 is traditional
    "金": ["钅", "釒"],
    # 糸: 纟 (simplified-left) is dominant; 糹 is the half-width traditional form
    "糸": ["纟", "糹"],
    # 月: no variant cards needed
    # 草艹: 艹 (top) is the productive form
    "艸": ["艹"],
    # 雨: rendered as-is on top — no major variant
}

# When the source col 1 is a `(pr.X)` style note instead of a simplified
# variant, parse the X out into the pinyin/note instead of treating it as a
# variant. Pattern detected: `(pr.<something>)`.
PR_NOTE_RE = re.compile(r"^\s*\(pr\.([^)]+)\)\s*$")


# ---------------------------------------------------------------------------
# Tier classification — based on a curated list of high-productivity / well-
# known radicals, the rest fall into 'common' / 'rare' / 'structural' by a
# simple heuristic until HanziCraft enrichment provides productivity counts.
# ---------------------------------------------------------------------------

_CORE_RADICALS = set("氵心钅木口亻艹丶辶宀广疒目人女子刀力又又水火金土山日月儿大不工竹米贝鸟马鱼车页革马门阝口")
# Radicals that exist almost purely as structural strokes — rarely meaning-bearing
_STRUCTURAL_RADICALS = set("一丨丶丿乙亅二亠儿入八冂冖凵几勹匕匚匸卜厂厶夕夂夊")
# Rare classical/specialized
_RARE_RADICALS = set("龜龍鼠鹿黍黻黼鬥鬯鬲鬼黾鼎鼓鼻齒齊麻麦麻黾鼎鼓鼠鼻齒齊龍龜韭")


def classify_tier(radical: str) -> str:
    if radical in _CORE_RADICALS:
        return "radical-core"
    if radical in _STRUCTURAL_RADICALS:
        return "radical-structural"
    if radical in _RARE_RADICALS:
        return "radical-rare"
    return "radical-common"


# ---------------------------------------------------------------------------
# Manual meaning overrides (when source gloss is too terse or missing)
# ---------------------------------------------------------------------------

MEANING_OVERRIDES: dict[str, str] = {
    # Filled lazily after spot-check
}


# ---------------------------------------------------------------------------
# Curated notes overrides (R3 will populate this — for now keep empty)
# ---------------------------------------------------------------------------

NOTE_OVERRIDES: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Source reader
# ---------------------------------------------------------------------------


def read_source(path: Path, log: list[str]) -> list[tuple[int, list[str]]]:
    """Read the 6-col seed TSV. Returns list of (line_no, fields) tuples."""
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    rows: list[tuple[int, list[str]]] = []
    line_no = 0
    for raw in text.split("\n"):
        line_no += 1
        if not raw.strip():
            continue
        if raw.lstrip().startswith("#"):
            continue
        fields = raw.split("\t")
        # Pad to 6
        while len(fields) < 6:
            fields.append("")
        rows.append((line_no, fields))
    log.append(f"read {len(rows)} non-empty, non-directive rows from source")
    return rows


# ---------------------------------------------------------------------------
# Per-row transform
# ---------------------------------------------------------------------------


COL0_VARIANTS_RE = re.compile(r"^([^\s(（]+)\s*[(（]([^)）]*)[)）]\s*$")


def parse_col0(value: str) -> tuple[str, list[str]]:
    """`心 (忄,⺗)` → (`心`, [`忄`, `⺗`]). `一` → (`一`, [])."""
    s = value.strip()
    m = COL0_VARIANTS_RE.match(s)
    if m:
        canonical = m.group(1).strip()
        variants_raw = m.group(2)
        # Variants are comma- or space-separated
        variants = [v.strip() for v in re.split(r"[,，\s]+", variants_raw) if v.strip()]
        return canonical, variants
    return s, []


def parse_pinyin_field(value: str) -> tuple[str, str]:
    """Returns (primary_pinyin, extra_for_note). Handles `yòng (shuǎi)` and
    `chuò / zouzhi` style fields."""
    s = value.strip()
    if not s:
        return "", ""
    # `chuò / zouzhi` — drop the `zouzhi` style spelling-out
    if "/" in s:
        parts = [p.strip() for p in s.split("/") if p.strip()]
        # Keep the part with tone-marks (most likely actual pinyin)
        keep = [p for p in parts if any(ch in _TONE_MAP for ch in p)]
        if keep:
            return keep[0], ""
        return parts[0], ""
    # `yòng (shuǎi)` — primary in front, alternate in parens
    m = re.match(r"^([^\s(（]+)\s*[(（]([^)）]+)[)）]\s*$", s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return s, ""


def normalize_member_chars(value: str) -> str:
    """Strip separators and non-CJK noise; keep only CJK chars in order."""
    out: list[str] = []
    for ch in value:
        if HAN_RE.match(ch):
            out.append(ch)
    return "".join(out)


def transform_row(
    fields: list[str],
    line_no: int,
    log: list[str],
) -> list[str] | None:
    """Map a 6-col source row → 15-col output row. Returns None to skip."""
    while len(fields) < 6:
        fields.append("")

    canonical_trad, variants_in_parens = parse_col0(fields[0])
    col1_raw = fields[1].strip()
    pinyin_field = fields[2]
    meaning = fields[3].strip()
    examples = fields[4]

    # Decide canonical (modern simplified preferred).
    canonical: str
    extra_variants: list[str] = []
    pronunciation_note = ""

    if col1_raw:
        m = PR_NOTE_RE.match(col1_raw)
        if m:
            pronunciation_note = m.group(1).strip()
            canonical = canonical_trad
            extra_variants = list(variants_in_parens)
        elif len(col1_raw) == 1 and HAN_RE.match(col1_raw):
            # Simplified-variant CJK char → promote to canonical.
            canonical = col1_raw
            # The original col-0 char becomes a traditional variant.
            extra_variants = [canonical_trad] + list(variants_in_parens)
        else:
            # Unknown col-1 content — log and treat as note material.
            log.append(
                f"line {line_no}: unexpected col-1 value {col1_raw!r} on radical "
                f"{canonical_trad!r}; ignoring"
            )
            canonical = canonical_trad
            extra_variants = list(variants_in_parens)
    else:
        canonical = canonical_trad
        extra_variants = list(variants_in_parens)

    if not canonical or not HAN_RE.match(canonical):
        log.append(
            f"line {line_no}: skipping row with non-CJK canonical {canonical!r}"
        )
        return None

    # Apply variant order override if present.
    if canonical in VARIANT_OVERRIDES:
        ordered = VARIANT_OVERRIDES[canonical]
        # Keep only variants we actually have, preserving override order.
        known = set(extra_variants)
        primary = [v for v in ordered if v in known]
        remainder = [v for v in extra_variants if v not in ordered]
        extra_variants = primary + remainder

    # Split into slots.
    variant1 = extra_variants[0] if len(extra_variants) >= 1 else ""
    variant2 = extra_variants[1] if len(extra_variants) >= 2 else ""
    reference_variants = ",".join(extra_variants[2:]) if len(extra_variants) > 2 else ""

    # Pinyin.
    primary_pinyin, alt_pinyin = parse_pinyin_field(pinyin_field)
    if pronunciation_note and not alt_pinyin:
        alt_pinyin = pronunciation_note

    # Meaning override.
    if canonical in MEANING_OVERRIDES:
        meaning = MEANING_OVERRIDES[canonical]

    member_chars = normalize_member_chars(examples)

    # Note assembly.
    note_extras: list[str] = []
    # Distinguish trad form when canonical differs.
    if canonical != canonical_trad:
        note_extras.append(f"Traditional: {canonical_trad}")
    if alt_pinyin:
        note_extras.append(f"Also reads: {alt_pinyin}")
    if canonical in NOTE_OVERRIDES:
        curated = NOTE_OVERRIDES[canonical].strip()
        if curated:
            note_extras.append(curated)
    note = "<br>".join(note_extras)

    # Link: HanziCraft URL covering radical + member chars (same pattern as
    # phonetic components).
    link_target = canonical + member_chars
    link = HANZICRAFT_URL.format(urllib.parse.quote(link_target))

    # Key: `<canonical>:<numeric-pinyin>`. Multi-reading radicals (rare) get
    # separate rows in the future if needed.
    key_pinyin = pinyin_marks_to_numeric(primary_pinyin) or f"row{line_no}"
    key = f"{canonical}:{key_pinyin}"

    # Tier tag.
    tier = classify_tier(canonical)
    tags = f"kangxi-radical {tier}"

    return [
        key,
        canonical,
        variant1,
        variant2,
        reference_variants,
        primary_pinyin,
        meaning,
        member_chars,
        "",            # Productivity — filled by R2 enrichment
        "",            # Frequency — filled by R2 enrichment
        "",            # Decomposition — filled by R2
        "",            # MemberDecomp — filled by R2
        note,
        link,
        tags,
    ]


# ---------------------------------------------------------------------------
# TSV writer
# ---------------------------------------------------------------------------


def sanitize_field(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    s = s.replace("\t", " ")
    return s


def write_output(rows: list[list[str]], out_path: Path) -> None:
    header_col_count = len(RADICALS_HEADER)
    header_line = "\t".join(RADICALS_HEADER)
    lines: list[str] = [
        "#separator:tab",
        "#html:true",
        f"#columns:{header_line}",
        f"#tags column:{header_col_count}",
    ]
    for r in rows:
        if len(r) != header_col_count:
            raise ValueError(f"row has wrong column count: {r!r}")
        lines.append("\t".join(sanitize_field(f) for f in r))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Sort key — radicals for learning order
# ---------------------------------------------------------------------------

# Tier weight: core first, then common, then structural, then rare.
_TIER_RANK = {
    "radical-core": 0,
    "radical-common": 1,
    "radical-structural": 2,
    "radical-rare": 3,
}


def sort_key(row: list[str]) -> tuple:
    """Sort by tier first (core → common → structural → rare), then by member-
    char count descending (more curated examples = higher priority within tier),
    then by canonical + pinyin for stability."""
    canonical = row[1]
    pinyin = row[5]
    member_chars = row[7]
    tags_field = row[14]
    tier = "radical-common"
    for t in tags_field.split():
        if t in _TIER_RANK:
            tier = t
            break
    return (
        _TIER_RANK.get(tier, 1),
        -len(member_chars),
        canonical,
        pinyin,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=RADICALS_DECK_PATH)
    args = ap.parse_args()

    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 1

    log: list[str] = []
    src_rows = read_source(args.source, log)

    out_rows: list[list[str]] = []
    seen: dict[str, int] = {}
    for line_no, fields in src_rows:
        try:
            row = transform_row(fields, line_no, log)
        except Exception as e:
            log.append(f"line {line_no}: transform error: {e!r}; skipping")
            continue
        if row is None:
            continue
        key = row[0]
        if key in seen:
            log.append(
                f"line {line_no}: duplicate Key {key!r} (first at line {seen[key]}); dropping"
            )
            continue
        seen[key] = line_no
        out_rows.append(row)

    out_rows.sort(key=sort_key)

    write_output(out_rows, args.out)

    for line in log:
        print(line, file=sys.stderr)
    print(
        f"\nwrote {args.out.name}: {len(out_rows)} rows "
        f"(from {len(src_rows)} source rows, {len(log)} log entries)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
