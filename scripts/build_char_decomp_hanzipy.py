#!/usr/bin/env python3
"""Build scripts/cache/char_decomp_hanzipy.json — comprehensive, accurate
per-character decomposition for the Kangxi-radicals deck.

Source: the `hanzipy` package (offline, ~12k chars, cjk-decomp data). Unlike the
HanziCraft-derived char_decomp.json (~2440 chars, too sparse and shape-polluted —
it lists 颈 under 川, 戴 under 矛), hanzipy decomposes correctly: 颈 = 龴+工+页
(no 川), 戴 = 戈-based (no 矛). The radicals importer uses this to (a) drop member
chars that don't actually contain the radical and (b) render every member's
breakdown on Card 4.

BUILD-TIME tool: hanzipy is only needed to (re)generate the cache. The importer
reads the committed JSON — no runtime hanzipy dependency.

Run after adding new characters / radicals to the deck:
  pip install hanzipy && python scripts/build_char_decomp_hanzipy.py
"""
from __future__ import annotations

import json
from pathlib import Path

from hanzipy.decomposer import HanziDecomposer

from common import HAN_RE
from components_common import parse_component_tsv, COMPONENT_DECK_PATH
from radicals_common import parse_radicals_tsv, RADICALS_DECK_PATH

CACHE = Path(__file__).resolve().parent / "cache"
OUT = CACHE / "char_decomp_hanzipy.json"


def main() -> int:
    chars: set[str] = set()
    # Every char in char_data (the cwc union — all member candidates), plus both
    # decks' own chars, so the cache is stable across deck regenerations.
    char_data = json.loads((CACHE / "char_data.json").read_text(encoding="utf-8"))
    chars.update(k for k in char_data if len(k) == 1)
    for parse, path in ((parse_component_tsv, COMPONENT_DECK_PATH),
                        (parse_radicals_tsv, RADICALS_DECK_PATH)):
        _, rows = parse(path)
        for r in rows:
            blob = "".join(getattr(r, f, "") for f in
                           ("radical", "variant1", "variant2", "reference_variants",
                            "component", "member_chars", "same_syllable_chars"))
            chars.update(HAN_RE.findall(blob))

    dec = HanziDecomposer()
    out: dict[str, dict] = {}
    for ch in sorted(chars):
        try:
            r = dec.decompose(ch)
        except Exception:
            continue
        once = [p for p in (r.get("once") or [])]
        radical = [p for p in (r.get("radical") or [])]
        # skip atomic / self-only results (no useful breakdown)
        useful = [p for p in once + radical if p and p != "No glyph available" and p != ch]
        if not useful:
            continue
        out[ch] = {"once": once, "radical": radical}

    OUT.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(out)} chars decomposed (of {len(chars)} seen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
