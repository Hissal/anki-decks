#!/usr/bin/env python3
"""Apply Breakdown / Examples backfill from a JSON file to a TSV.

JSON shape:
  {
    "<hanzi>": {
      "breakdown": "char (gloss) char (gloss) ...",
      "examples": ["中文。 / English.", "中文。 / English.", "中文。 / English."]
    },
    ...
  }

Either `breakdown` or `examples` (or both) may be present per entry. Examples
is a list of 1-3 strings; they get joined with `<br>` on write. Existing
non-empty Breakdown / Examples values in the TSV are never overwritten.

Usage:
  python scripts/apply_backfill.py <tsv-name> <data.json>          # dry-run
  python scripts/apply_backfill.py <tsv-name> <data.json> --apply  # write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tsv", help="TSV filename at the repo root")
    ap.add_argument("data", help="path to JSON file with hanzi -> {breakdown, examples}")
    ap.add_argument("--apply", action="store_true", help="write changes to disk")
    args = ap.parse_args()

    tsv_path = REPO_ROOT / args.tsv
    data_path = Path(args.data)
    if not tsv_path.exists():
        print(f"tsv not found: {tsv_path}", file=sys.stderr)
        return 2
    if not data_path.exists():
        print(f"data not found: {data_path}", file=sys.stderr)
        return 2

    data: dict[str, dict] = json.loads(data_path.read_text(encoding="utf-8"))

    text = tsv_path.read_text(encoding="utf-8-sig")
    lines = text.replace("\r\n", "\n").split("\n")
    trailing_newline = text.endswith("\n")

    new_lines: list[str] = []
    applied_break = 0
    applied_examples = 0
    untouched = 0

    for line in lines:
        if not line or line.startswith("#"):
            new_lines.append(line)
            continue
        fields = line.split("\t")
        if len(fields) < 8:
            new_lines.append(line)
            continue
        hanzi = fields[0]
        entry = data.get(hanzi)
        if not entry:
            new_lines.append(line)
            untouched += 1
            continue

        # Column indices: 3 = Breakdown, 4 = Examples.
        if not fields[3].strip() and entry.get("breakdown"):
            fields[3] = entry["breakdown"]
            applied_break += 1
        if not fields[4].strip() and entry.get("examples"):
            ex = entry["examples"]
            if isinstance(ex, list):
                ex = "<br>".join(ex)
            fields[4] = ex
            applied_examples += 1
        new_lines.append("\t".join(fields))

    out = "\n".join(new_lines)
    if trailing_newline and not out.endswith("\n"):
        out += "\n"

    print(f"{args.tsv}: breakdown {applied_break}, examples {applied_examples}, "
          f"untouched data-entries {untouched}")
    if args.apply:
        tsv_path.write_text(out, encoding="utf-8", newline="")
        print(f"  -> wrote {args.tsv}")
    else:
        print("  (dry-run; pass --apply to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
