#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the corrected "Finland subdivisions" deck from its downloaded source.

The upstream community deck (a CrowdAnki export reusing the Ultimate Geography
note type, 19 Finnish regions) ships only four card templates and no blank
locator map. This script regenerates `deck.json` from `deck.source.json`:

  1. derive `media/_Finland_base.png` — the blank Finland locator base, = the
     per-channel median of the same-size region maps (`*_sijainti_Suomi*`) with
     the red highlight masked out (same trick as make_ug_world_base.py);
  2. add the two missing templates: Country - Flag and Country - Map (the latter
     uses the blank base as its front, mirroring the Ultimate Geography decks);
  3. reorder all six templates into the studied sequence + renumber `ord`;
  4. rebuild the ord-indexed `req` array to match.

Idempotent: always starts from `deck.source.json`. Re-run after editing the
source or adding region maps. Needs numpy + PIL (build-time only).
"""

import copy
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

OUT_DIR = Path(__file__).resolve().parent / "Finland_subdivisions"
SRC = OUT_DIR / "deck.source.json"
OUT = OUT_DIR / "deck.json"
MEDIA = OUT_DIR / "media"
BASE_NAME = "_Finland_base.png"

TEMPLATE_ORDER = [
    "Country - Map",       # 0  place region on map (blank Finland front)
    "Map - Country",       # 1  name the highlighted region
    "Flag - Country",      # 2  name region from coat of arms
    "Capital - Country",   # 3  capital -> region
    "Country - Capital",   # 4  region -> capital
    "Country - Flag",      # 5  region -> coat of arms (loose recall)
]

# req entry by template name: (kind, [field_idx]).
# fields: Country=0 Capital=2 Flag=5 Map=7. Forward "Country->X" = all; reverse = any.
REQ = {
    "Country - Map":     ("all", [7]),
    "Map - Country":     ("any", [7]),
    "Flag - Country":    ("any", [5]),
    "Capital - Country": ("any", [2]),
    "Country - Capital": ("all", [2]),
    "Country - Flag":    ("all", [5]),
}

# Stock Ultimate Geography flag-shaped placeholder (no "blank flag" concept).
FLAG_OVAL = (
    '    <svg\n'
    '      class="placeholder"\n'
    '      xmlns="http://www.w3.org/2000/svg"\n'
    '      width="417"\n'
    '      height="250"\n'
    '      viewBox="0 0 417 250"\n'
    '    >\n'
    '      <path d="m2 26s45-24 129-24c86 0 146 25 210 25 64 0 74-10 74-10v218s-25 '
    '13-83 13-146-25-206-25c-60 0-123 19-123 19z" />\n'
    '    </svg>'
)


def build_base() -> tuple:
    """Median-rebuild the blank Finland locator into media/_Finland_base.png."""
    files = sorted(f for f in MEDIA.glob("*sijainti*") if not f.name.startswith("_"))
    if not files:
        raise SystemExit(f"no *sijainti* region maps found in {MEDIA}")
    size = Counter(Image.open(f).size for f in files).most_common(1)[0][0]
    grp = [f for f in files if Image.open(f).size == size]
    stack = np.stack(
        [np.asarray(Image.open(f).convert("RGB"), dtype=np.float64) for f in grp], 0)
    red = (stack[..., 0] > 120) & (stack[..., 1] < 90) & (stack[..., 2] < 90)
    stack[red] = np.nan
    base = np.nan_to_num(np.nanmedian(stack, axis=0), nan=255.0)
    out = np.clip(base, 0, 255).astype(np.uint8)
    Image.fromarray(out, "RGB").save(MEDIA / BASE_NAME)
    left = int(((out[..., 0] > 120) & (out[..., 1] < 90) & (out[..., 2] < 90)).sum())
    return size, len(grp), len(files), left


def _tmpl(proto: dict, name: str, qfmt: str, afmt: str) -> dict:
    t = copy.deepcopy(proto)
    t["name"], t["qfmt"], t["afmt"] = name, qfmt, afmt
    return t


def main() -> None:
    size, n, total, left = build_base()
    print(f"base: {n}/{total} maps @ {size[0]}x{size[1]}, red left={left} -> {BASE_NAME}")

    deck = json.loads(SRC.read_text(encoding="utf-8"))
    nm = deck["note_models"][0]
    tmpls = {t["name"]: t for t in nm["tmpls"]}
    proto = tmpls["Country - Capital"]

    cflag_q = (
        '{{#Flag}}\n'
        '  <div class="value value--top">{{Country}}</div>\n'
        '  {{#Country info}}<div class="info">{{Country info}}</div>{{/Country info}}\n\n'
        '  <hr>\n\n'
        '  <div class="type">Flag</div>\n'
        '  <div class="value value--image">\n' + FLAG_OVAL + '\n'
        '  </div>\n'
        '{{/Flag}}'
    )
    cflag_a = (
        '<div class="value value--top">{{Country}}</div>\n'
        '{{#Country info}}<div class="info">{{Country info}}</div>{{/Country info}}\n\n'
        '<hr id=answer>\n\n'
        '<div class="type">Flag</div>\n'
        '<div class="value value--image value--back">{{Flag}}</div>\n'
        '{{#Flag similarity}}<div class="info">Flag similar to {{Flag similarity}}.</div>'
        '{{/Flag similarity}}'
    )
    cmap_q = (
        '{{#Map}}\n'
        '  <div class="value value--top">{{Country}}</div>\n\n'
        '  <hr>\n\n'
        '  <div class="type">Location</div>\n'
        '  <div class="value value--image"><img src="' + BASE_NAME + '" /></div>\n'
        '{{/Map}}'
    )
    cmap_a = (
        '<div class="value value--top">{{Country}}</div>\n'
        '{{#Country info}}<div class="info">{{Country info}}</div>{{/Country info}}\n\n'
        '<hr id=answer>\n\n'
        '<div class="type">Location</div>\n'
        '<div class="value value--image">{{Map}}</div>'
    )

    tmpls["Country - Flag"] = _tmpl(proto, "Country - Flag", cflag_q, cflag_a)
    tmpls["Country - Map"] = _tmpl(proto, "Country - Map", cmap_q, cmap_a)

    ordered = [tmpls[name] for name in TEMPLATE_ORDER]
    for i, t in enumerate(ordered):
        t["ord"] = i
    nm["tmpls"] = ordered
    nm["req"] = [[i, REQ[t["name"]][0], REQ[t["name"]][1]] for i, t in enumerate(ordered)]

    OUT.write_text(
        json.dumps(deck, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("templates:", [f"{t['ord']}:{t['name']}" for t in ordered])
    print(f"notes: {len(deck['notes'])} -> {OUT.name}")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    main()
