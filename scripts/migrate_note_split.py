#!/usr/bin/env python3
"""One-shot migration: split the Note column into Breakdown / Examples / Note / Link.

Old schema:  Hanzi  Pinyin  English  Note  Tags                                 (5 cols)
New schema:  Hanzi  Pinyin  English  Breakdown  Examples  Note  Link  Tags      (8 cols)

Rules:
  - Idioms deck (Chinese_Idioms_Proverbs_Classical.tsv): every Note ends with a
    char-gloss line, separated from preceding prose by literal `<br>`. Split on
    the LAST `<br>` — trailing part → Breakdown, preceding part → Note.
  - Core / Slang decks: no Breakdown convention; Breakdown stays empty.
  - All decks: any `Example: 中文。 / English.` lines in the remaining Note get
    extracted into Examples (one per line, `Example: ` prefix stripped). Anything
    else stays in Note.
  - Link column starts empty for every row.
  - Updates the `#columns:` and `#tags column:` directives.
  - Idempotent: if a file is already in the new 8-column schema, it is skipped.

Usage:
  python scripts/migrate_note_split.py            # dry run, prints summary
  python scripts/migrate_note_split.py --apply    # writes changes
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

OLD_COLUMNS = "Hanzi\tPinyin\tEnglish\tNote\tTags"
NEW_COLUMNS = "Hanzi\tPinyin\tEnglish\tBreakdown\tExamples\tNote\tLink\tTags"

IDIOMS_FILE = "Chinese_Idioms_Proverbs_Classical.tsv"


def split_breakdown(note: str, is_idioms: bool) -> tuple[str, str]:
    """Returns (breakdown, remaining_note). Splits only for idioms deck."""
    if not is_idioms or "<br>" not in note:
        return "", note
    head, _, tail = note.rpartition("<br>")
    return tail.strip(), head.strip()


def extract_examples(note: str) -> tuple[str, str]:
    """Pull `Example: …` lines out of note. Returns (examples_field, remaining_note).

    Examples field contains one example per literal newline character, prefix
    stripped. Tabs/newlines inside fields will be escaped to spaces by the
    writer below.
    """
    if not note:
        return "", ""
    # Split note on either literal \n or <br> for sentence boundaries.
    # Most existing rows have all text on one line — split on `Example:` prefix.
    parts = re.split(r"(?=Example:\s*)", note)
    examples: list[str] = []
    leftover: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("Example:"):
            examples.append(part[len("Example:"):].strip())
        else:
            leftover.append(part)
    return "\n".join(examples), " ".join(leftover).strip()


def process_file(path: Path, apply: bool) -> tuple[int, str]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.replace("\r\n", "\n").split("\n")
    trailing_newline = text.endswith("\n")

    is_idioms = path.name == IDIOMS_FILE

    # Detect schema by reading the #columns directive.
    columns_line = next((l for l in lines if l.startswith("#columns:")), None)
    if columns_line is None:
        return 0, f"{path.name}: no #columns directive, skipping"
    if columns_line == f"#columns:{NEW_COLUMNS}":
        return 0, f"{path.name}: already in new schema, skipping"
    if columns_line != f"#columns:{OLD_COLUMNS}":
        return 0, f"{path.name}: unexpected #columns directive {columns_line!r}, skipping"

    new_lines: list[str] = []
    changed = 0

    for line in lines:
        if line.startswith("#columns:"):
            new_lines.append(f"#columns:{NEW_COLUMNS}")
            continue
        if line.startswith("#tags column:"):
            new_lines.append("#tags column:8")
            continue
        if not line or line.startswith("#"):
            new_lines.append(line)
            continue

        fields = line.split("\t")
        if len(fields) != 5:
            # Defensively pad / truncate — wrong column count is a separate issue.
            while len(fields) < 5:
                fields.append("")
            fields = fields[:5]

        hanzi, pinyin, english, note, tags = fields

        breakdown, remaining = split_breakdown(note, is_idioms)
        examples, final_note = extract_examples(remaining)

        new_fields = [
            hanzi,
            pinyin,
            english,
            breakdown,
            examples.replace("\t", " "),
            final_note.replace("\t", " "),
            "",  # Link (empty for now)
            tags,
        ]
        # Note: Examples may contain literal \n inside the field; that's encoded
        # as \\n in TSV-land. Anki TSV doesn't support newlines mid-field, so we
        # use a special separator. Anki accepts `<br>` in fields with #html:true.
        new_fields[4] = examples.replace("\n", "<br>").replace("\t", " ")

        new_lines.append("\t".join(new_fields))
        changed += 1

    if apply:
        out = "\n".join(new_lines)
        if trailing_newline and not out.endswith("\n"):
            out += "\n"
        path.write_text(out, encoding="utf-8", newline="")
        return changed, f"{path.name}: wrote {changed} row(s)"
    return changed, f"{path.name}: would change {changed} row(s)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes to disk")
    args = ap.parse_args()

    paths = sorted(REPO_ROOT.glob("*.tsv"))
    if not paths:
        print("no .tsv files found", file=sys.stderr)
        return 1

    total = 0
    for p in paths:
        n, msg = process_file(p, apply=args.apply)
        total += n
        print(msg)
    print(f"\nsummary: {total} row(s) {'changed' if args.apply else 'would change'}")
    if not args.apply:
        print("dry-run only. re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
