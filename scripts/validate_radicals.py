#!/usr/bin/env python3
"""Validate Chinese_Kangxi_Radicals.tsv.

Hard errors fail exit code 1.

Hard errors:
  - missing/wrong directives or #columns header
  - row has wrong column count
  - empty Key / Radical / Pinyin / Meaning / MemberChars
  - Radical has no CJK character or more than one CJK character
  - Variant1 / Variant2 contain non-CJK or the same char as Radical
  - duplicate Key

Soft warnings:
  - Productivity / Frequency present but not an integer
  - Link present but doesn't look like a URL
  - Row missing a tier tag (kangxi-radical alone is too coarse)
"""

from __future__ import annotations

import argparse
import re
import sys

from common import HAN_RE, stderr
from radicals_common import (
    RADICALS_DECK_PATH,
    RADICALS_COLUMN_COUNT,
    parse_radicals_tsv,
)

LINK_RE = re.compile(r"^https?://")
INT_RE = re.compile(r"^\d+$")
TIER_TAGS = {"radical-core", "radical-common", "radical-structural", "radical-rare"}


def deep_checks(rows, path) -> tuple[list[str], list[str]]:
    """Simplified-only + structural invariants from the R3 cleanup:
      - no traditional member char / variant (opencc)            [ERROR]
      - the Radical itself must not be in its own MemberChars     [ERROR]
      - each positional variant is represented in the set        [WARN]
    Auto-skips if opencc / cwc cache is unavailable."""
    try:
        import json
        from opencc import OpenCC
        from import_kangxi_radicals import VARIANT_EXAMPLE_OVERRIDES, DEFAULT_CWC_CACHE
        t2s = OpenCC("t2s")
        cwc = (json.loads(DEFAULT_CWC_CACHE.read_text(encoding="utf-8"))
               if DEFAULT_CWC_CACHE.exists() else {})
    except Exception as e:  # pragma: no cover
        return [], [f"deep checks skipped (opencc/cwc unavailable): {e}"]

    def is_trad(c): return len(c) == 1 and t2s.convert(c) != c
    def simp_cwc(k): return {t2s.convert(c) for c in cwc.get(k, [])}

    errors: list[str] = []
    warnings: list[str] = []
    for r in rows:
        loc = f"{path.name}:{r.line_no}"
        members = HAN_RE.findall(r.member_chars)
        for c in members:
            if is_trad(c):
                errors.append(f"{loc}: MemberChars has traditional char {c!r}")
            if c == r.radical:
                errors.append(f"{loc}: MemberChars contains the Radical itself {c!r}")
        for slot, v in (("Variant1", r.variant1), ("Variant2", r.variant2)):
            if v and is_trad(v):
                errors.append(f"{loc}: {slot} {v!r} is traditional — belongs in the Note")
        mset = set(members)
        for v in (r.variant1, r.variant2):
            if not v:
                continue
            rep = bool(mset & simp_cwc(v)) or VARIANT_EXAMPLE_OVERRIDES.get(v) in mset
            if not rep:
                warnings.append(f"{loc}: Variant {v!r} has no char representing it in MemberChars")
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    ap.add_argument("--no-deep", action="store_true",
                    help="skip simplified-only / representation semantic checks")
    args = ap.parse_args()

    path = RADICALS_DECK_PATH
    if not path.exists():
        stderr(f"error: {path.name} not found at repo root")
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    try:
        _header, rows = parse_radicals_tsv(path)
    except ValueError as e:
        stderr(f"error: {e}")
        return 1

    raw_lines = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n")
    for i, line in enumerate(raw_lines, start=1):
        if not line.strip() or line.startswith("#"):
            continue
        n = len(line.split("\t"))
        if n != RADICALS_COLUMN_COUNT:
            errors.append(
                f"{path.name}:{i}: wrong column count "
                f"(expected {RADICALS_COLUMN_COUNT}, got {n})"
            )

    seen_keys: dict[str, int] = {}

    for r in rows:
        loc = f"{path.name}:{r.line_no}"

        if not r.key:
            errors.append(f"{loc}: empty Key")
        elif r.key in seen_keys:
            errors.append(
                f"{loc}: duplicate Key {r.key!r} (also at {path.name}:{seen_keys[r.key]})"
            )
        else:
            seen_keys[r.key] = r.line_no

        if not r.radical:
            errors.append(f"{loc}: empty Radical")
        else:
            han_chars = HAN_RE.findall(r.radical)
            if not han_chars:
                errors.append(
                    f"{loc}: Radical {r.radical!r} has no CJK character"
                )
            elif len(han_chars) > 1:
                errors.append(
                    f"{loc}: Radical {r.radical!r} has more than one CJK character"
                )

        if not r.pinyin:
            errors.append(f"{loc}: empty Pinyin")
        if not r.meaning:
            warnings.append(f"{loc}: empty Meaning (Radical {r.radical!r})")
        if not r.member_chars:
            warnings.append(f"{loc}: empty MemberChars (Radical {r.radical!r})")

        for slot, val in (("Variant1", r.variant1), ("Variant2", r.variant2)):
            if not val:
                continue
            if not HAN_RE.match(val):
                errors.append(f"{loc}: {slot} {val!r} is not a CJK character")
            elif val == r.radical:
                errors.append(f"{loc}: {slot} duplicates Radical {r.radical!r}")

        if r.productivity and not INT_RE.match(r.productivity):
            errors.append(f"{loc}: Productivity {r.productivity!r} is not an integer")
        if r.frequency and not INT_RE.match(r.frequency):
            errors.append(f"{loc}: Frequency {r.frequency!r} is not an integer")
        if r.link and not LINK_RE.match(r.link):
            warnings.append(f"{loc}: Link {r.link!r} doesn't look like a URL")

        if not any(t in TIER_TAGS for t in r.tags):
            warnings.append(
                f"{loc}: Radical {r.radical!r} has no tier tag (one of {sorted(TIER_TAGS)})"
            )

    if not args.no_deep:
        de, dw = deep_checks(rows, path)
        errors.extend(de)
        warnings.extend(dw)

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
