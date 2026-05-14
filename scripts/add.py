#!/usr/bin/env python3
"""Interactive helper to append a row to one of the deck TSVs.

Prompts for each field, escapes tabs and newlines, checks for duplicate Hanzi
across all decks, validates tags against TAGS.md, and asks for confirmation
before writing.

Usage:
  python scripts/add.py            # picks deck interactively
  python scripts/add.py core       # core / idioms / slang
"""

from __future__ import annotations

import sys
from pathlib import Path

from common import (
    DECKS,
    REPO_ROOT,
    TIER_TAGS,
    append_row,
    deck_paths,
    has_ascii_letter,
    has_han,
    load_allowed_tags,
    looks_like_digit_pinyin,
    parse_tsv,
    stderr,
)


def prompt(label: str, *, allow_empty: bool = False) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value or allow_empty:
            return value
        print("  required.")


def pick_deck(arg: str | None) -> Path:
    if arg:
        key = arg.lower()
        if key not in DECKS:
            stderr(f"unknown deck {arg!r}. choose from: {', '.join(DECKS)}")
            sys.exit(2)
        return REPO_ROOT / DECKS[key]

    print("decks:")
    keys = list(DECKS)
    for i, k in enumerate(keys, start=1):
        print(f"  {i}) {k:<7}  ({DECKS[k]})")
    while True:
        choice = input("pick deck (number or name): ").strip().lower()
        if choice in DECKS:
            return REPO_ROOT / DECKS[choice]
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            return REPO_ROOT / DECKS[keys[int(choice) - 1]]
        print("  invalid choice.")


def all_existing_hanzi() -> dict[str, tuple[str, int]]:
    out: dict[str, tuple[str, int]] = {}
    for p in deck_paths():
        try:
            _, rows = parse_tsv(p)
        except ValueError as e:
            stderr(f"warn: could not parse {p.name}: {e}")
            continue
        for r in rows:
            if r.hanzi and r.hanzi not in out:
                out[r.hanzi] = (p.name, r.line_no)
    return out


def main() -> int:
    deck_arg = sys.argv[1] if len(sys.argv) > 1 else None
    deck_path = pick_deck(deck_arg)
    print(f"-> appending to {deck_path.name}\n")

    existing = all_existing_hanzi()
    allowed_tags = load_allowed_tags()

    while True:
        hanzi = prompt("Hanzi")
        if not has_han(hanzi):
            print("  no CJK characters detected. try again.")
            continue
        if has_ascii_letter(hanzi):
            print("  warning: Hanzi contains ASCII letters.")
        if hanzi in existing:
            other_file, other_line = existing[hanzi]
            print(f"  duplicate: already in {other_file}:{other_line}. choose another.")
            continue
        break

    while True:
        pinyin = prompt("Pinyin (with tone marks)")
        if looks_like_digit_pinyin(pinyin):
            confirm = input("  looks like digit tones (ni3hao3). keep anyway? [y/N] ")
            if confirm.strip().lower() != "y":
                continue
        break

    english = prompt("English (use / to separate senses)")
    note = prompt("Note (optional; include Example: 中文 / English)", allow_empty=True)

    print("\ntiers: production-ready, recognition-ready, recognition-first")
    while True:
        tier = prompt("tier tag").strip()
        if tier in TIER_TAGS:
            break
        print(f"  must be one of {sorted(TIER_TAGS)}.")

    extra = input("extra tags (space-separated, optional): ").strip()
    tags = [tier] + [t for t in extra.split() if t]

    if allowed_tags:
        unknown = [t for t in tags if t not in allowed_tags]
        if unknown:
            print(f"  warning: tags not in TAGS.md: {unknown}")
            confirm = input("  proceed anyway? [y/N] ")
            if confirm.strip().lower() != "y":
                print("aborted.")
                return 1

    fields = [hanzi, pinyin, english, note, " ".join(tags)]
    print("\nrow to append:")
    for label, value in zip(
        ["Hanzi", "Pinyin", "English", "Note", "Tags"], fields
    ):
        print(f"  {label:<7} {value}")

    confirm = input("\nwrite? [Y/n] ").strip().lower()
    if confirm in ("", "y", "yes"):
        append_row(deck_path, fields)
        print(f"appended to {deck_path.name}.")
        return 0
    print("aborted.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\naborted.")
        sys.exit(130)
