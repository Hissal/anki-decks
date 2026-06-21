#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build an English-first / Finnish-annotated Ultimate Geography [Extended] deck.

Same source deck as build_ultimate_geography_fi.py, but the answer fields read
"<English> (<Finnish>)" instead of "<Finnish> (<English>)", and the descriptive
fields (Country info, Capital info, Capital hint, Flag similarity) are kept in the
ORIGINAL ENGLISH. In other words: the stock English deck with the Finnish name
added in parentheses on the Country and Capital fields.

Reuses the verified FI_PLACE / FI_CAPITAL name maps from the sibling script so the
two decks can never disagree on a name. New deck identity + new note guids so this
deck coexists with the EN, ZH and FI decks in one Anki collection.
"""

import hashlib
import json
import shutil
from pathlib import Path

from build_ultimate_geography_fi import EN_DIR, FI_PLACE, FI_CAPITAL, _BASE91
from make_ug_world_base import (
    build_world_base,
    patch_country_map_front,
    reorder_templates,
)

OUT_DIR = Path(__file__).resolve().parent / "Ultimate Geography [EN-FI] [Extended]"

FI_DECK_UUID = "1d7e84b3-6c2a-4f5d-8b91-3e6a2f0c7d51"
FI_DECK_NAME = "Ultimate Geography [EN-FI]"


def guid(name: str) -> str:
    """Deterministic 10-char base91 guid, salted distinctly from the other decks."""
    num = int(hashlib.sha256(("UG-ENFI-v1:" + name).encode("utf-8")).hexdigest(), 16)
    out = ""
    while num and len(out) < 10:
        num, rem = divmod(num, 91)
        out = _BASE91[rem] + out
    return out.rjust(10, _BASE91[0])


def fmt(en: str, fi: str) -> str:
    """Answer-field format: English (Finnish)."""
    return f"{en} ({fi})"


def main() -> None:
    en_deck = json.loads((EN_DIR / "deck.json").read_text(encoding="utf-8"))

    # every name must be mappable (descriptive fields are kept as-is, no map needed)
    missing = set()
    for n in en_deck["notes"]:
        f = n["fields"]
        if f[0].strip() and f[0] not in FI_PLACE:
            missing.add(("place", f[0]))
        if f[2].strip() and f[2] not in FI_CAPITAL:
            missing.add(("capital", f[2]))
    if missing:
        for k, s in sorted(missing):
            print(f"MISSING [{k}] {s!r}")
        raise SystemExit(1)

    seen: set[str] = set()
    notes = []
    for n in en_deck["notes"]:
        f = list(n["fields"])
        new = list(f)
        new[0] = fmt(f[0], FI_PLACE[f[0]]) if f[0].strip() else f[0]
        new[2] = fmt(f[2], FI_CAPITAL[f[2]]) if f[2].strip() else f[2]
        # fields 1,3,4,6 (info/hint/flag-similarity) and 5,7 (Flag/Map) stay verbatim
        g = guid(f[0])
        assert g not in seen, f"guid collision for {f[0]}"
        seen.add(g)
        note = dict(n)
        note["fields"] = new
        note["guid"] = g
        notes.append(note)

    deck = dict(en_deck)
    deck["crowdanki_uuid"] = FI_DECK_UUID
    deck["name"] = FI_DECK_NAME
    deck["notes"] = notes
    # desc stays the original English description (English-first deck)

    # blank world map on the Country - Map front (see make_ug_world_base.py)
    front_patched = patch_country_map_front(deck["note_models"])
    reorder_templates(deck["note_models"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "deck.json").write_text(
        json.dumps(deck, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    src_media = EN_DIR / "media"
    dst_media = OUT_DIR / "media"
    if dst_media.exists():
        shutil.rmtree(dst_media)
    shutil.copytree(src_media, dst_media)

    # derive the blank world locator map into this deck's media
    build_world_base(dst_media)

    print(f"Wrote {OUT_DIR / 'deck.json'}")
    print(f"Notes: {len(notes)} | media files copied: {len(list(dst_media.iterdir()))} "
          f"| Country-Map front patched: {front_patched}")


if __name__ == "__main__":
    main()
