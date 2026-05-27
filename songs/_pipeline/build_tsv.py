"""Build SongLine TSVs — emits TWO files because Anki's Cloze note type
can't host non-cloze card templates, so we use two note types:

  <Out>_Basic.tsv  → SongLineBasic note type   (Recall-line + Reading cards)
  <Out>_Cloze.tsv  → SongLineCloze note type   (word-level cloze cards)

Both files share the per-line `Key` (`<slug>_<NNN>`). Re-importing either
updates by Key.

Inside SongLineBasic the templates are ordered Recall (Card 1) → Reading
(Card 2). Combined with import order — Cloze.tsv first, then Block.tsv,
then Basic.tsv last — that produces the deck-wide intro order:

  Cloze cards → Block cards → Recall cards → Reading cards
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


def _basic_columns() -> list[str]:
    return [
        "Key", "SongSlug", "LineNo", "HanziPlain", "Pinyin", "English",
        "Breakdown", "Audio", "PrevHanzi", "PrevAudio", "Tags",
    ]


def _cloze_columns() -> list[str]:
    return [
        "Key", "SongSlug", "LineNo", "Hanzi", "Pinyin", "English",
        "Breakdown", "Audio", "Tags",
    ]


def _header(cols: list[str]) -> list[str]:
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
    """Wrap each cloze word with `{{cN::word}}` markers, numbered by list order."""
    out = hanzi
    for i, word in enumerate(clozes, 1):
        if word not in out:
            print(f"  warn: cloze word '{word}' not found in line '{hanzi}' — skipping")
            continue
        out = out.replace(word, f"{{{{c{i}::{word}}}}}", 1)
    return out


def build(
    aligned: list[dict],
    english: list[str],
    breakdown: list[str],
    cloze_plan: dict,
    prefix: str,
    song_slug: str,
    tags_base: list[str],
) -> tuple[list[list[str]], list[list[str]]]:
    """Return (basic_rows, cloze_rows)."""
    assert len(english) == len(aligned) == len(breakdown)
    by_line_no = {entry["line_no"]: entry for entry in cloze_plan["lines"]}
    basic_rows: list[list[str]] = []
    cloze_rows: list[list[str]] = []
    seen: set[str] = set()
    skipped: list[int] = []
    for i, (row, en, bd) in enumerate(zip(aligned, english, breakdown), 1):
        hanzi = row["line"]
        if hanzi in seen:
            skipped.append(i)
            continue
        seen.add(hanzi)
        py = line_pinyin(hanzi)
        audio = f"[sound:{prefix}_{i:03d}.mp3]"
        prev_hanzi = aligned[i - 2]["line"] if i >= 2 else ""
        prev_audio = f"[sound:{prefix}_{i - 1:03d}.mp3]" if i >= 2 else ""
        key = f"{song_slug}_{i:03d}"
        line_no = str(i)
        tags = " ".join(tags_base + [f"line-{i:03d}"])

        basic_rows.append([
            key, song_slug, line_no, hanzi, py, en, bd, audio,
            prev_hanzi, prev_audio, tags,
        ])

        clozes = by_line_no.get(i, {}).get("selected_clozes", [])
        if clozes:
            hanzi_with_cloze = inject_clozes(hanzi, clozes)
            cloze_rows.append([
                key, song_slug, line_no, hanzi_with_cloze, py, en, bd, audio, tags,
            ])
        else:
            print(f"  info: line {i:03d} has no clozes — skipping Cloze TSV row")
    if skipped:
        print(f"  dedup skipped {len(skipped)} duplicate line(s): {skipped}")
    return basic_rows, cloze_rows


def write_tsv(path: Path, cols: list[str], rows: list[list[str]]):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for line in _header(cols):
            f.write(line + "\n")
        for row in rows:
            f.write("\t".join(row) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aligned", required=True, type=Path)
    ap.add_argument("--english", required=True, type=Path)
    ap.add_argument("--breakdown", required=True, type=Path)
    ap.add_argument("--cloze-plan", required=True, type=Path)
    ap.add_argument("--out-stem", required=True, type=Path,
                    help="e.g. .../Chinese_Song_Yi_Jian_Mei_Lines — _Basic.tsv and _Cloze.tsv get appended")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--song-slug", required=True)
    ap.add_argument("--tag", action="append", default=[])
    args = ap.parse_args()

    aligned = json.loads(args.aligned.read_text(encoding="utf-8"))
    english = [ln.rstrip("\n") for ln in args.english.read_text(encoding="utf-8").splitlines() if ln.strip()]
    breakdown = [ln.rstrip("\n") for ln in args.breakdown.read_text(encoding="utf-8").splitlines() if ln.strip()]
    cloze_plan = yaml.safe_load(args.cloze_plan.read_text(encoding="utf-8"))

    basic_rows, cloze_rows = build(
        aligned, english, breakdown, cloze_plan,
        args.prefix, args.song_slug, args.tag,
    )

    basic_path = args.out_stem.with_name(args.out_stem.name + "_Basic.tsv")
    cloze_path = args.out_stem.with_name(args.out_stem.name + "_Cloze.tsv")
    write_tsv(basic_path, _basic_columns(), basic_rows)
    write_tsv(cloze_path, _cloze_columns(), cloze_rows)
    print(f"wrote {len(basic_rows)} basic rows -> {basic_path}")
    print(f"wrote {len(cloze_rows)} cloze rows -> {cloze_path}")


if __name__ == "__main__":
    main()
