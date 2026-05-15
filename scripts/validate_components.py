#!/usr/bin/env python3
"""Validate Chinese_Phonetic_Components.tsv.

Sibling of validate.py — the components deck has a different schema, so it
gets its own validator. Hard errors fail with exit code 1.

Hard errors:
  - missing/wrong directives or #columns header
  - row has wrong column count
  - empty Key / Component / Pinyin / MemberChars
  - Component has no CJK character
  - Component contains more than one CJK character (defensive — phase 1 keeps
    single-char components only)
  - Pinyin still uses digit tones (e.g. li3) instead of tone marks
  - MemberChars still contains the Component itself
  - duplicate Key

Soft warnings:
  - missing Meaning
  - Audio is set but doesn't look like `[sound:….mp3]`

Usage:
  python scripts/validate_components.py            # validate
  python scripts/validate_components.py --strict   # warnings also fail
"""

from __future__ import annotations

import argparse
import re
import sys

from common import HAN_RE, DIGIT_TONE_RE, stderr
from components_common import (
    COMPONENT_DECK_PATH,
    COMPONENT_COLUMN_COUNT,
    parse_component_tsv,
)

AUDIO_RE = re.compile(r"^\[sound:[^\]]+\.mp3\]$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    args = ap.parse_args()

    path = COMPONENT_DECK_PATH
    if not path.exists():
        stderr(f"error: {path.name} not found at repo root")
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    try:
        _header, rows = parse_component_tsv(path)
    except ValueError as e:
        stderr(f"error: {e}")
        return 1

    # Column-count check on raw lines (parse_component_tsv pads short rows).
    raw_lines = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n")
    for i, line in enumerate(raw_lines, start=1):
        if not line.strip() or line.startswith("#"):
            continue
        n = len(line.split("\t"))
        if n != COMPONENT_COLUMN_COUNT:
            errors.append(
                f"{path.name}:{i}: wrong column count "
                f"(expected {COMPONENT_COLUMN_COUNT}, got {n})"
            )

    seen_keys: dict[str, int] = {}

    for r in rows:
        loc = f"{path.name}:{r.line_no}"

        if not r.key:
            errors.append(f"{loc}: empty Key")
        elif r.key in seen_keys:
            errors.append(
                f"{loc}: duplicate Key {r.key!r} "
                f"(also at {path.name}:{seen_keys[r.key]})"
            )
        else:
            seen_keys[r.key] = r.line_no

        if not r.component:
            errors.append(f"{loc}: empty Component")
        else:
            han_chars = HAN_RE.findall(r.component)
            if not han_chars:
                errors.append(
                    f"{loc}: Component {r.component!r} has no CJK character"
                )
            elif len(han_chars) > 1:
                errors.append(
                    f"{loc}: Component {r.component!r} has more than one CJK "
                    f"character ({len(han_chars)})"
                )

        if not r.pinyin:
            errors.append(f"{loc}: empty Pinyin")
        elif DIGIT_TONE_RE.search(r.pinyin.lower()):
            errors.append(
                f"{loc}: Pinyin {r.pinyin!r} appears to use digit tones; "
                f"expected tone marks"
            )

        if not r.member_chars:
            errors.append(f"{loc}: empty MemberChars")
        elif r.component and r.component in r.member_chars:
            errors.append(
                f"{loc}: MemberChars {r.member_chars!r} still contains Component "
                f"{r.component!r}; strip it"
            )

        if not r.meaning:
            warnings.append(f"{loc}: empty Meaning (Component {r.component!r})")

        if r.audio and not AUDIO_RE.match(r.audio):
            warnings.append(
                f"{loc}: Audio {r.audio!r} doesn't look like a [sound:…\\.mp3] ref"
            )

    for w in warnings:
        stderr(f"warn: {w}")
    for e in errors:
        stderr(f"error: {e}")

    print(
        f"\nchecked {path.name}: {len(rows)} rows · "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    )

    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
