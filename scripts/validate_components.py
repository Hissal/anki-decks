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
LINK_RE = re.compile(r"^https?://")
INT_RE = re.compile(r"^\d+$")
DECOMP_RE = re.compile(r"^(once:[^;]+)?(?:;?radical:[^;]+)?$")


def deep_checks(rows, path) -> tuple[list[str], list[str]]:
    """Semantic invariants the structural pass can't catch:
      - simplified-only: no traditional Component / member char (opencc)   [ERROR]
      - containment: every member/SS char actually contains the Component
        (cwc raw membership or decomposition)                             [ERROR]
      - tone buckets: MemberChars = exact syllable+tone; SameSyllableChars
        = same syllable, different tone (pypinyin heteronyms)             [WARN]

    Tone is a warning, not an error: pypinyin can miss a rare reading, and we
    don't want a false negative to fail CI. Containment/simplified are reliable.
    Auto-skips (with one warning) if the cwc cache or pypinyin/opencc are absent.
    """
    try:
        import json
        from import_phonetic_components import (
            component_contains, char_readings, primary_reading, to_simplified,
            strip_tone, _norm_syllable, DEFAULT_CWC, DEFAULT_CHAR_DECOMP,
        )
        cwc = json.loads(DEFAULT_CWC.read_text(encoding="utf-8")) if DEFAULT_CWC.exists() else None
        char_decomp = (json.loads(DEFAULT_CHAR_DECOMP.read_text(encoding="utf-8"))
                       if DEFAULT_CHAR_DECOMP.exists() else None)
    except Exception as e:  # pragma: no cover - environment-dependent
        return [], [f"deep checks skipped (pypinyin/opencc/cwc unavailable): {e}"]
    if cwc is None:
        return [], ["deep checks skipped: component_cwc.json cache missing"]

    errors: list[str] = []
    warnings: list[str] = []
    for r in rows:
        loc = f"{path.name}:{r.line_no}"
        comp = r.component
        keypin = r.key.split(":", 1)[1] if ":" in r.key else ""
        exp = (_norm_syllable(strip_tone(keypin)),
               int(keypin[-1]) if keypin and keypin[-1].isdigit() else 5)
        if comp and to_simplified(comp) != comp:
            errors.append(f"{loc}: Component {comp!r} is traditional; deck is simplified-only")
        for ch in HAN_RE.findall(r.member_chars):
            if to_simplified(ch) != ch:
                errors.append(f"{loc}: MemberChars has traditional char {ch!r}")
            if comp and not component_contains(comp, ch, cwc, char_decomp)[0]:
                errors.append(f"{loc}: MemberChars {ch!r} does not contain Component {comp!r}")
            rds = char_readings(ch)
            if rds and exp not in rds:
                warnings.append(f"{loc}: MemberChars {ch!r} lacks exact tone {keypin!r} (readings {rds})")
        for ch in HAN_RE.findall(r.same_syllable_chars):
            if to_simplified(ch) != ch:
                errors.append(f"{loc}: SameSyllableChars has traditional char {ch!r}")
            if comp and not component_contains(comp, ch, cwc, char_decomp)[0]:
                errors.append(f"{loc}: SameSyllableChars {ch!r} does not contain Component {comp!r}")
            if primary_reading(ch) == exp:
                warnings.append(f"{loc}: SameSyllableChars {ch!r} primary reading is exact tone {keypin!r}; belongs in MemberChars")
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    ap.add_argument("--no-deep", action="store_true",
                    help="skip containment/tone/simplified semantic checks")
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

        if r.same_syllable_chars:
            if r.component and r.component in r.same_syllable_chars:
                errors.append(
                    f"{loc}: SameSyllableChars still contains Component {r.component!r}"
                )
            overlap = set(r.member_chars) & set(r.same_syllable_chars)
            if overlap:
                errors.append(
                    f"{loc}: SameSyllableChars overlaps MemberChars on {sorted(overlap)!r}"
                )

        if not r.meaning:
            warnings.append(f"{loc}: empty Meaning (Component {r.component!r})")

        if r.audio and not AUDIO_RE.match(r.audio):
            warnings.append(
                f"{loc}: Audio {r.audio!r} doesn't look like a [sound:…\\.mp3] ref"
            )

        if r.productivity and not INT_RE.match(r.productivity):
            errors.append(
                f"{loc}: Productivity {r.productivity!r} is not an integer"
            )
        if r.frequency and not INT_RE.match(r.frequency):
            errors.append(
                f"{loc}: Frequency {r.frequency!r} is not an integer"
            )
        if r.link and not LINK_RE.match(r.link):
            warnings.append(
                f"{loc}: Link {r.link!r} doesn't look like a URL"
            )

        if r.decomposition and not DECOMP_RE.match(r.decomposition):
            errors.append(
                f"{loc}: Decomposition {r.decomposition!r} doesn't match "
                f"the expected `once:X+Y;radical:Z` format"
            )

        if r.member_decomp:
            for entry in r.member_decomp.split("|"):
                if "=" not in entry:
                    errors.append(
                        f"{loc}: MemberDecomp entry {entry!r} missing `=`"
                    )
                    break
                ch, rhs = entry.split("=", 1)
                if not ch or not rhs:
                    errors.append(
                        f"{loc}: MemberDecomp entry {entry!r} has empty char or decomp"
                    )
                    break

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
