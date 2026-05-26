"""Build the SongBlock TSV (one note per N-line block).

Each block becomes a single Anki Cloze note. Every line in the block is
wrapped in its own `{{cN::}}` marker, so the note generates one card per
line — each card hides ONE whole line while showing the others.

`BlockAudio` exploits the cloze grouping: each `{{cN::}}` wraps a single
pre-baked combo mp3 ref. Anki shows only the matching card's contents,
so each card plays exactly its combo file (the version with silence in
the blanked slot).

Schema:
  Key  SongSlug  BlockNo  Lines  Pinyin  English  Breakdown
  BlockAudio  Tags
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

import yaml
from pypinyin import pinyin, Style

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


CJK_RE = re.compile(r"[㐀-鿿]")


def _columns() -> list[str]:
    return [
        "Key", "SongSlug", "BlockNo", "Lines", "Pinyin", "English",
        "Breakdown", "BlockAudio", "Tags",
    ]


def header() -> list[str]:
    cols = _columns()
    return [
        "#separator:tab",
        "#html:true",
        "#columns:" + "\t".join(cols),
        f"#tags column:{len(cols)}",
    ]


def line_pinyin(hanzi: str) -> str:
    syllables = pinyin(hanzi, style=Style.TONE, heteronym=False, errors="ignore")
    return " ".join(s[0].lower() for s in syllables if s and s[0])


def merge_breakdown(breakdown_lines: list[str]) -> str:
    """Concatenate `char (gloss)` tokens across the block, dedup by char,
    preserving first-appearance order."""
    seen: set[str] = set()
    parts: list[str] = []
    for line in breakdown_lines:
        for tok in line.split():
            # tok like `真` (start of a `char (gloss)` pair) or `(true)` (gloss)
            if CJK_RE.match(tok[:1]):
                ch = tok[0]
                if ch in seen:
                    continue
                seen.add(ch)
                parts.append(tok)
            else:
                # Append the gloss/parenthetical to the most recent char part.
                if parts and not parts[-1].endswith(")"):
                    parts[-1] = parts[-1] + " " + tok
                elif parts:
                    # Already complete; tok might be a continuation we want to
                    # ignore to avoid double-glossing.
                    pass
    return " ".join(parts)


def build_rows(
    blocks_plan: dict,
    english: list[str],
    breakdown: list[str],
    aligned_lines: list[dict],
    prefix: str,
    song_slug: str,
    tags_base: list[str],
) -> list[list[str]]:
    rows: list[list[str]] = []
    for block in blocks_plan["blocks"]:
        b_no = block["block_no"]
        line_nos = block["line_nos"]
        # Build cloze-wrapped Lines field.
        cloze_lines = []
        audio_pieces = []
        pinyin_lines = []
        english_lines = []
        breakdown_lines = []
        for k, n in enumerate(line_nos, 1):
            hanzi = aligned_lines[n - 1]["line"]
            cloze_lines.append(f"{{{{c{k}::{hanzi}}}}}")
            audio_pieces.append(
                f"{{{{c{k}::[sound:{prefix}_block_{b_no:02d}_c{k}.mp3]}}}}"
            )
            pinyin_lines.append(line_pinyin(hanzi))
            english_lines.append(english[n - 1])
            breakdown_lines.append(breakdown[n - 1])
        lines_field = "<br>".join(cloze_lines)
        audio_field = "".join(audio_pieces)
        pinyin_field = "<br>".join(pinyin_lines)
        english_field = "<br>".join(english_lines)
        breakdown_field = merge_breakdown(breakdown_lines)
        key = f"{song_slug}_block_{b_no:02d}"
        tags = " ".join(tags_base + [f"block-{b_no:02d}"])
        rows.append([
            key, song_slug, str(b_no), lines_field, pinyin_field, english_field,
            breakdown_field, audio_field, tags,
        ])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", required=True, type=Path)
    ap.add_argument("--aligned", required=True, type=Path)
    ap.add_argument("--english", required=True, type=Path)
    ap.add_argument("--breakdown", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--song-slug", required=True)
    ap.add_argument("--tag", action="append", default=[])
    args = ap.parse_args()

    blocks_plan = yaml.safe_load(args.blocks.read_text(encoding="utf-8"))
    aligned = json.loads(args.aligned.read_text(encoding="utf-8"))
    english = [ln.rstrip("\n") for ln in args.english.read_text(encoding="utf-8").splitlines() if ln.strip()]
    breakdown = [ln.rstrip("\n") for ln in args.breakdown.read_text(encoding="utf-8").splitlines() if ln.strip()]

    rows = build_rows(blocks_plan, english, breakdown, aligned, args.prefix, args.song_slug, args.tag)

    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for line in header():
            f.write(line + "\n")
        for row in rows:
            f.write("\t".join(row) + "\n")
    print(f"wrote {len(rows)} SongBlock rows -> {args.out}")


if __name__ == "__main__":
    main()
