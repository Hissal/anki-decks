"""Build the SongLine TSV (one note per lyric line).

Schema (matches the SongLine note-type design):

  Key  SongSlug  LineNo  Hanzi  Pinyin  English  Breakdown  Audio
  PrevHanzi  PrevAudio  Tags

- `Hanzi` has `{{cN::word}}` markers wrapping each `selected_clozes` word
  from cloze_plan.yaml, numbered in order of appearance in the list.
- `PrevHanzi` / `PrevAudio` point at the line immediately before this one
  in the song (the position-based predecessor), regardless of whether that
  line was deduped away as a duplicate.
- Re-importing this TSV updates by `Key` (first column) — same Anki rule
  as the word decks.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import yaml
from pypinyin import pinyin, Style

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _columns() -> list[str]:
    return [
        "Key", "SongSlug", "LineNo", "Hanzi", "Pinyin", "English",
        "Breakdown", "Audio", "PrevHanzi", "PrevAudio", "Tags",
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


def inject_clozes(hanzi: str, clozes: list[str]) -> str:
    """Wrap each cloze word with `{{cN::word}}` markers, numbered by list order.

    First occurrence wins (substring replace). If a word isn't found in the
    line, prints a warning and skips it.
    """
    out = hanzi
    for i, word in enumerate(clozes, 1):
        if word not in out:
            print(f"  warn: cloze word '{word}' not found in line '{hanzi}' — skipping")
            continue
        out = out.replace(word, f"{{{{c{i}::{word}}}}}", 1)
    return out


def build_rows(
    aligned: list[dict],
    english: list[str],
    breakdown: list[str],
    cloze_plan: dict,
    prefix: str,
    song_slug: str,
    tags_base: list[str],
) -> list[list[str]]:
    assert len(english) == len(aligned) == len(breakdown)
    by_line_no = {entry["line_no"]: entry for entry in cloze_plan["lines"]}
    rows: list[list[str]] = []
    seen: set[str] = set()
    skipped: list[int] = []
    for i, (row, en, bd) in enumerate(zip(aligned, english, breakdown), 1):
        hanzi = row["line"]
        if hanzi in seen:
            skipped.append(i)
            continue
        seen.add(hanzi)
        clozes = by_line_no.get(i, {}).get("selected_clozes", [])
        hanzi_with_cloze = inject_clozes(hanzi, clozes)
        py = line_pinyin(hanzi)
        audio = f"[sound:{prefix}_{i:03d}.mp3]"
        prev_hanzi = aligned[i - 2]["line"] if i >= 2 else ""
        prev_audio = f"[sound:{prefix}_{i - 1:03d}.mp3]" if i >= 2 else ""
        key = f"{song_slug}_{i:03d}"
        line_no = str(i)
        tags = " ".join(tags_base + [f"line-{i:03d}"])
        rows.append([
            key, song_slug, line_no, hanzi_with_cloze, py, en, bd, audio,
            prev_hanzi, prev_audio, tags,
        ])
    if skipped:
        print(f"  dedup skipped {len(skipped)} duplicate line(s): {skipped}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aligned", required=True, type=Path)
    ap.add_argument("--english", required=True, type=Path)
    ap.add_argument("--breakdown", required=True, type=Path)
    ap.add_argument("--cloze-plan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--song-slug", required=True)
    ap.add_argument("--tag", action="append", default=[])
    args = ap.parse_args()

    aligned = json.loads(args.aligned.read_text(encoding="utf-8"))
    english = [ln.rstrip("\n") for ln in args.english.read_text(encoding="utf-8").splitlines() if ln.strip()]
    breakdown = [ln.rstrip("\n") for ln in args.breakdown.read_text(encoding="utf-8").splitlines() if ln.strip()]
    cloze_plan = yaml.safe_load(args.cloze_plan.read_text(encoding="utf-8"))
    rows = build_rows(aligned, english, breakdown, cloze_plan, args.prefix, args.song_slug, args.tag)

    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for line in header():
            f.write(line + "\n")
        for row in rows:
            f.write("\t".join(row) + "\n")
    print(f"wrote {len(rows)} SongLine rows -> {args.out}")


if __name__ == "__main__":
    main()
