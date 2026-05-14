#!/usr/bin/env python3
"""Validate every deck TSV in the repo.

Hard errors (exit code 1):
  - missing or wrong header
  - row has wrong column count
  - empty Hanzi / Pinyin / English column
  - duplicate Hanzi within a single deck
  - duplicate Hanzi across decks
  - Hanzi column has no CJK character at all

Soft warnings (exit code 0 unless --strict):
  - row has no tier tag (production-ready / recognition-ready / recognition-first)
  - tag is not listed in TAGS.md
  - Pinyin column uses digit tones (e.g. ni3hao3) instead of tone marks
  - Hanzi column contains ASCII letters

Usage:
  python scripts/validate.py            # validate
  python scripts/validate.py --strict   # warnings also fail
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from common import (
    COLUMN_COUNT,
    EXPECTED_HEADER,
    TIER_TAGS,
    deck_paths,
    has_ascii_letter,
    has_han,
    load_allowed_tags,
    looks_like_digit_pinyin,
    parse_tsv,
    stderr,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    allowed_tags = load_allowed_tags()
    if not allowed_tags:
        warnings.append("TAGS.md not found or empty — tag allowlist check skipped")

    seen_hanzi_global: dict[str, tuple[Path, int]] = {}

    paths = deck_paths()
    if not paths:
        errors.append("no .tsv files found at repo root")

    for path in paths:
        try:
            _header, rows = parse_tsv(path)
        except ValueError as e:
            errors.append(str(e))
            continue

        # Re-read raw lines for column-count check (parse_tsv normalizes width).
        # Skip blank lines and Anki TSV directives (lines starting with `#`).
        raw_lines = (
            path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n")
        )
        for i, line in enumerate(raw_lines, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) != COLUMN_COUNT:
                errors.append(
                    f"{path.name}:{i}: wrong column count "
                    f"(expected {COLUMN_COUNT}, got {len(fields)})"
                )

        seen_in_file: dict[str, int] = {}
        for r in rows:
            loc = f"{path.name}:{r.line_no}"

            if not r.hanzi:
                errors.append(f"{loc}: empty Hanzi")
            elif not has_han(r.hanzi):
                errors.append(f"{loc}: Hanzi column has no CJK character: {r.hanzi!r}")
            elif has_ascii_letter(r.hanzi):
                warnings.append(f"{loc}: Hanzi contains ASCII letters: {r.hanzi!r}")

            if not r.pinyin:
                errors.append(f"{loc}: empty Pinyin")
            elif looks_like_digit_pinyin(r.pinyin):
                warnings.append(
                    f"{loc}: Pinyin appears to use digit tones, expected diacritics: "
                    f"{r.pinyin!r}"
                )

            if not r.english:
                errors.append(f"{loc}: empty English")

            if r.hanzi:
                if r.hanzi in seen_in_file:
                    errors.append(
                        f"{loc}: duplicate Hanzi {r.hanzi!r} "
                        f"(also at {path.name}:{seen_in_file[r.hanzi]})"
                    )
                else:
                    seen_in_file[r.hanzi] = r.line_no

                if r.hanzi in seen_hanzi_global:
                    other_path, other_line = seen_hanzi_global[r.hanzi]
                    if other_path != path:
                        errors.append(
                            f"{loc}: Hanzi {r.hanzi!r} also in "
                            f"{other_path.name}:{other_line}"
                        )
                else:
                    seen_hanzi_global[r.hanzi] = (path, r.line_no)

            # Tag checks.
            if r.tags:
                if not any(t in TIER_TAGS for t in r.tags):
                    warnings.append(f"{loc}: no tier tag - add one of {sorted(TIER_TAGS)}")
                if allowed_tags:
                    for t in r.tags:
                        if t not in allowed_tags:
                            warnings.append(
                                f"{loc}: tag {t!r} not in TAGS.md allowlist"
                            )
            else:
                warnings.append(f"{loc}: no tags")

    for w in warnings:
        stderr(f"warn: {w}")
    for e in errors:
        stderr(f"error: {e}")

    print(
        f"\nchecked {len(paths)} file(s): "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    )

    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
