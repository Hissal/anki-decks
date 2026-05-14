#!/usr/bin/env python3
"""One-shot migration: rewrite the Pinyin column to strict 1-syllable-per-CJK.

Reads each deck TSV, regenerates the Pinyin column via pypinyin (contextual,
heteronym=False), preserves all other columns and directives. Flags rows
where the new diacritic stream disagrees with the old one — those are
polyphone misses (了 le/liǎo, 行 xíng/háng, 重 zhòng/chóng, etc.) that need
manual review.

Operates on whatever column shape the file currently has — does not depend
on scripts/common.py's EXPECTED_HEADER, so it works both before and after
the note/examples/breakdown migration. The Pinyin column is always the
second TSV column.

Setup:
  pip install pypinyin

Usage:
  python scripts/migrate_pinyin_per_char.py            # dry run, prints diff
  python scripts/migrate_pinyin_per_char.py --apply    # writes changes
  python scripts/migrate_pinyin_per_char.py --apply --force-all  # apply even on disagreement (not recommended)
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

try:
    from pypinyin import Style, lazy_pinyin
except ImportError:
    print("pypinyin not installed. run: pip install pypinyin", file=sys.stderr)
    sys.exit(2)


# Tone-mark mapping. Used by the 一 / 不 sandhi post-processor to detect the
# tone of the following syllable.
_TONE1 = "āēīōūǖ"
_TONE2 = "áéíóúǘ"
_TONE3 = "ǎěǐǒǔǚ"
_TONE4 = "àèìòùǜ"


def _syllable_tone(syl: str) -> int | None:
    """Return 1/2/3/4 if any vowel in `syl` carries that tone, else None (neutral)."""
    for ch in syl:
        if ch in _TONE1:
            return 1
        if ch in _TONE2:
            return 2
        if ch in _TONE3:
            return 3
        if ch in _TONE4:
            return 4
    return None


def _apply_yi_bu_sandhi(syllables: list[str]) -> list[str]:
    """Apply morpheme-level 一 and 不 sandhi.

      一 yī → yí before tone-4
      一 yī → yì before tones 1/2/3
      一 yī (final / before nothing / neutral) → yī
      不 bù → bú before tone-4
      不 bù otherwise → bù
    """
    out = list(syllables)
    for i, syl in enumerate(out):
        nxt = out[i + 1] if i + 1 < len(out) else None
        nxt_tone = _syllable_tone(nxt) if nxt else None
        if syl == "yī" and nxt_tone is not None:
            out[i] = "yí" if nxt_tone == 4 else "yì"
        elif syl == "bù" and nxt_tone == 4:
            out[i] = "bú"
    return out

REPO_ROOT = Path(__file__).resolve().parent.parent
HAN_RE = re.compile(r"[㐀-䶿一-鿿]")


def is_han(ch: str) -> bool:
    return bool(HAN_RE.match(ch))


def regenerate_pinyin(hanzi: str) -> str:
    """One pinyin syllable per CJK char, lowercase, space-joined.

    Drops non-Han chars from pypinyin output via `errors=lambda c: ''`. Result
    has exactly len([c for c in hanzi if is_han(c)]) tokens.
    """
    raw = lazy_pinyin(hanzi, style=Style.TONE, errors=lambda c: "")
    syllables = [t.lower() for t in raw if t]
    syllables = _apply_yi_bu_sandhi(syllables)
    return " ".join(syllables)


def strip_diacritics(s: str) -> str:
    """NFD-decompose, drop combining marks, lowercase. For tone-mark comparison."""
    decomposed = unicodedata.normalize("NFD", s)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return plain.lower()


def diacritic_compare(old: str, new: str) -> bool:
    """True if old and new have the same pinyin letters (ignoring spaces / tones).

    Used to detect polyphone misses. Real disagreement = different letters.
    """
    old_plain = re.sub(r"\s+", "", strip_diacritics(old))
    new_plain = re.sub(r"\s+", "", strip_diacritics(new))
    return old_plain == new_plain


def tone_compare(old: str, new: str) -> bool:
    """True if tone-marked vowels match too. Stricter — used to detect tone misses."""
    old_letters = re.sub(r"\s+", "", old.lower())
    new_letters = re.sub(r"\s+", "", new.lower())
    return old_letters == new_letters


def process_file(path: Path, apply: bool, force_all: bool) -> tuple[int, int, int]:
    """Returns (changed, conflicts, ok)."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.replace("\r\n", "\n").split("\n")
    trailing_newline = text.endswith("\n")

    changed = 0
    conflicts = 0
    ok = 0
    new_lines: list[str] = []

    for i, line in enumerate(lines, start=1):
        if not line or line.startswith("#"):
            new_lines.append(line)
            continue

        fields = line.split("\t")
        if len(fields) < 2:
            new_lines.append(line)
            continue

        hanzi = fields[0]
        old_pinyin = fields[1]
        new_pinyin = regenerate_pinyin(hanzi)

        if old_pinyin == new_pinyin:
            ok += 1
            new_lines.append(line)
            continue

        letters_match = diacritic_compare(old_pinyin, new_pinyin)
        tones_match = tone_compare(old_pinyin, new_pinyin)

        if letters_match and tones_match:
            # Only spacing differs — safe.
            label = "spacing"
        elif letters_match:
            label = "tone-diff"
            conflicts += 1
        else:
            label = "POLYPHONE"
            conflicts += 1

        print(f"{path.name}:{i} [{label}] {hanzi}")
        print(f"  old: {old_pinyin!r}")
        print(f"  new: {new_pinyin!r}")

        if apply and (label == "spacing" or force_all):
            fields[1] = new_pinyin
            new_lines.append("\t".join(fields))
            changed += 1
        else:
            new_lines.append(line)

    if apply and changed:
        out = "\n".join(new_lines)
        if trailing_newline and not out.endswith("\n"):
            out += "\n"
        path.write_text(out, encoding="utf-8", newline="")
        print(f"-> wrote {changed} change(s) to {path.name}\n")
    else:
        print(f"-> {path.name}: {changed} would-change, {conflicts} conflict(s), {ok} unchanged\n")

    return changed, conflicts, ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes to disk")
    ap.add_argument(
        "--force-all",
        action="store_true",
        help="apply even on diacritic/polyphone disagreement (review output carefully first)",
    )
    args = ap.parse_args()

    paths = sorted(REPO_ROOT.glob("*.tsv"))
    if not paths:
        print("no .tsv files found at repo root", file=sys.stderr)
        return 1

    total_changed = 0
    total_conflicts = 0
    total_ok = 0
    for p in paths:
        c, conf, ok = process_file(p, apply=args.apply, force_all=args.force_all)
        total_changed += c
        total_conflicts += conf
        total_ok += ok

    print(f"summary: {total_changed} change(s), {total_conflicts} conflict(s), {total_ok} unchanged")
    if not args.apply:
        print("dry-run only. re-run with --apply to write changes.")
        print("conflicts require manual review (polyphone or tone-difference); re-run with --force-all to override.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
