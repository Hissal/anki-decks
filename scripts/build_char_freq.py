#!/usr/bin/env python3
"""Build scripts/cache/char_freq.json — per-character corpus frequency used to
weight the phonetic-components deck ordering ("what you'll actually see" first).

Source: the `wordfreq` package's Chinese (zh) data, as a Zipf value (log10 of
occurrences per billion; ~7 = extremely common like 的, ~5-6 = common, ~3 =
uncommon, <3 = rare/archaic, 0 = not attested). Zipf is already log-scaled, so
it sums cleanly in the sort score.

This is a BUILD-TIME tool: wordfreq is only needed to (re)generate the cache.
The importer reads the committed JSON and has no runtime wordfreq dependency —
matching the other scripts/cache/*.json files.

Run after adding new characters to the deck:
  pip install wordfreq && python scripts/build_char_freq.py
"""
from __future__ import annotations

import json
from pathlib import Path

from wordfreq import zipf_frequency

from components_common import parse_component_tsv, COMPONENT_DECK_PATH, HAN_RE
from radicals_common import parse_radicals_tsv, RADICALS_DECK_PATH

CACHE = Path(__file__).resolve().parent / "cache"
OUT = CACHE / "char_freq.json"


def main() -> int:
    chars: set[str] = set()
    # Superset: every char in char_data (union of all cwc lists) so the cache is
    # stable across deck regenerations, plus both decks' own chars.
    char_data = json.loads((CACHE / "char_data.json").read_text(encoding="utf-8"))
    chars.update(char_data.keys())
    _, rows = parse_component_tsv(COMPONENT_DECK_PATH)
    for r in rows:
        chars.add(r.component)
        chars.update(HAN_RE.findall(r.member_chars))
        chars.update(HAN_RE.findall(r.same_syllable_chars))
    # Radicals deck too — radicals/variants (飞 龟 …) aren't always in char_data,
    # and the radicals importer uses char_freq for backfill ranking + rare-tier.
    _, rrows = parse_radicals_tsv(RADICALS_DECK_PATH)
    for r in rrows:
        chars.update(HAN_RE.findall(r.radical + r.variant1 + r.variant2
                                    + r.reference_variants + r.member_chars))

    freq: dict[str, float] = {}
    for ch in sorted(chars):
        if len(ch) != 1:
            continue
        z = zipf_frequency(ch, "zh")
        if z > 0:  # omit zeros (absent ⇒ treated as 0 at lookup time)
            freq[ch] = round(z, 2)

    OUT.write_text(
        json.dumps(freq, ensure_ascii=False, sort_keys=True, indent=0),
        encoding="utf-8",
    )
    print(f"wrote {OUT.name}: {len(freq)} chars with freq (of {len(chars)} seen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
