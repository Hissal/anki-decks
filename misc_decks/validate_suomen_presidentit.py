#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the generated Suomen Presidentit deck.json (design spec §11).

Run from misc_decks/:  python validate_suomen_presidentit.py
Exit 0 = OK, 1 = problems listed.
"""

import json
import re
from pathlib import Path

DECK_DIR = Path(__file__).resolve().parent / "Suomen_presidentit"
DECK = DECK_DIR / "deck.json"
MEDIA = DECK_DIR / "media"
IMG_RE = re.compile(r'src="([^"]+)"')


def main() -> int:
    deck = json.loads(DECK.read_text(encoding="utf-8"))
    errors = []

    pres = deck["note_models"][0]
    fnames = [f["name"] for f in pres["flds"]]
    fidx = {n: i for i, n in enumerate(fnames)}

    # 14 templates, ord-indexed req of equal length.
    if len(pres["tmpls"]) != 14:
        errors.append(f"expected 14 president templates, got {len(pres['tmpls'])}")
    if [r[0] for r in pres["req"]] != list(range(len(pres["tmpls"]))):
        errors.append("president req is not ord-indexed 0..n")

    # New fields present.
    for need in ("Life", "Profession", "Birthplace", "KnownFor", "Nickname",
                 "Link", "Predecessor", "Successor"):
        if need not in fidx:
            errors.append(f"missing president field: {need}")

    # 13 president notes intact, full field width, non-empty guids.
    pres_notes = [n for n in deck["notes"]
                  if n["note_model_uuid"] == pres["crowdanki_uuid"]]
    if len(pres_notes) != 13:
        errors.append(f"expected 13 president notes, got {len(pres_notes)}")
    for n in pres_notes:
        if len(n["fields"]) != len(fnames):
            errors.append(f"note {n['guid']} has {len(n['fields'])} fields, "
                          f"model has {len(fnames)}")
        if not n["guid"]:
            errors.append("empty guid on a president note")

    # Years + Name normalized (no leftover HTML / nbsp).
    for n in pres_notes:
        yrs = n["fields"][fidx["Years"]]
        if "<" in yrs or "&nbsp;" in yrs:
            errors.append(f"Years not normalized: {yrs!r}")
        if "<" in n["fields"][fidx["Name"]]:
            errors.append(f"Name still has HTML: {n['fields'][fidx['Name']]!r}")

    # Every Link is a non-empty http(s) URL.
    for n in pres_notes:
        link = n["fields"][fidx["Link"]]
        if not link.startswith("http"):
            errors.append(f"bad/empty Link on note {n['guid']}: {link!r}")

    # Every <img> resolves to a media file.
    for n in pres_notes:
        for m in IMG_RE.findall(n["fields"][fidx["Image"]]):
            if not (MEDIA / m).exists():
                errors.append(f"missing media: {m}")

    # Aggregate notes present, tagged koonti.
    koonti = [n for n in deck["notes"] if "koonti" in n.get("tags", [])]
    if len(koonti) < 6:
        errors.append(f"expected >=6 koonti notes, got {len(koonti)}")

    # Guids unique across the whole deck.
    guids = [n["guid"] for n in deck["notes"]]
    if len(guids) != len(set(guids)):
        errors.append("duplicate guids in deck")

    # Party rosters partition the 13 presidents.
    roster_ans = [n["fields"][1] for n in koonti
                  if n["fields"][0].startswith("Luettele kaikki")]
    total = sum(a.count("(") for a in roster_ans)
    if total != 13:
        errors.append(f"party rosters cover {total} presidents, expected 13")

    if errors:
        print("FAIL:")
        for e in errors:
            print("  -", e)
        return 1
    print(f"OK: {len(pres_notes)} presidents, {len(koonti)} koonti notes, "
          f"{len(pres['tmpls'])} templates, rosters cover {total}.")
    return 0


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
