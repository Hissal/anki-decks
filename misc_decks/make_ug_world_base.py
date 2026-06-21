#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reconstruct a blank, label-free world locator map for the Ultimate Geography decks
and wire it onto the front of the "Country - Map" card.

Why this works
--------------
Ultimate Geography ships one map per continent / ocean as `ug-map-<X>-nobox.png`.
Each is the SAME world locator canvas (identical projection, land colours, borders,
sea) with exactly ONE region painted red. A given land pixel is red in at most one
continent map and no ocean map (and vice-versa for sea pixels), so masking the red
samples and taking the per-channel median across the dozen nobox maps rebuilds the
pristine, un-highlighted world map. (Same idea as make_china_base_map.py, but the
naive packed-RGB median used there only works when the base is pixel-identical AND
the highlight never overlaps; the nobox set has slight border antialiasing and a few
transcontinental pixels claimed twice, so we mask red + median per channel instead.)

The front of the stock "Country - Map" card shows a featureless oval placeholder, so
you must imagine the location from nothing before flipping. We swap that oval for the
blank world map (`_ug-world-blank.png`) — a real frame of reference — while the back
still reveals the regional map with the country highlighted. Mirrors the Chinese
geography deck's `locate` card, which puts `_China_base.png` on its front.

Run standalone to (re)apply to the already-built decks:

    python make_ug_world_base.py

or import `build_world_base` / `patch_country_map_front` from the build scripts so a
from-source rebuild stays correct.
"""

import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

BASE_NAME = "_ug-world-blank.png"

# Card order baked into the deck, matching the in-Anki reorder:
#   1 place country on map      2 name the highlighted country
#   3 name the country from flag 4 capital -> country
#   5 country -> capital         6 country -> flag (loose flag recall)
# Anki keys a card's scheduling to its template `ord`, so renumbering here only
# stays consistent on re-import because the collection's templates were already
# dragged into this same order (which renumbered their ords too).
TEMPLATE_ORDER = [
    "Country - Map",
    "Map - Country",
    "Flag - Country",
    "Capital - Country",
    "Country - Capital",
    "Country - Flag",
]

# The decks built by the sibling build_ultimate_geography_*.py scripts.
OUT_DIRS = [
    Path(__file__).resolve().parent / "Ultimate Geography [EN-FI] [Extended]",
    Path(__file__).resolve().parent / "Ultimate Geography [FI] [Extended]",
]

# Red-highlight test (the locator fill is a strong red; land/sea/borders are not).
def _red_mask(arr: np.ndarray) -> np.ndarray:
    return (arr[..., 0] > 140) & (arr[..., 1] < 110) & (arr[..., 2] < 110)


def build_world_base(media_dir: Path) -> Path:
    """Median-rebuild the blank world map into ``media_dir/_ug-world-blank.png``."""
    # NB: use pathlib glob, not glob.glob — the deck dir names contain "[...]"
    # which glob.glob would treat as a character class and never match.
    files = sorted(
        f for f in media_dir.glob("ug-map-*-nobox.png")
        if not f.name.startswith("_")
    )
    if not files:
        raise SystemExit(f"no ug-map-*-nobox.png maps found in {media_dir}")

    # All nobox maps share one canvas; guard against a stray odd size.
    from collections import Counter
    sizes = Counter(Image.open(f).size for f in files)
    target = sizes.most_common(1)[0][0]
    group = [f for f in files if Image.open(f).size == target]

    stack = np.stack(
        [np.asarray(Image.open(f).convert("RGB"), dtype=np.float64) for f in group],
        axis=0,
    )  # (N, H, W, 3)

    masked = stack.copy()
    masked[_red_mask(stack)] = np.nan
    base = np.nanmedian(masked, axis=0)          # red samples ignored
    base = np.nan_to_num(base, nan=230.0)        # safety: any all-red pixel -> land
    out = np.clip(base, 0, 255).astype(np.uint8)

    red_left = int(_red_mask(out).sum())
    dst = media_dir / BASE_NAME
    Image.fromarray(out, "RGB").save(dst)
    print(f"  {media_dir.parent.name or media_dir.name}: "
          f"{len(group)}/{len(files)} nobox maps @ {target[0]}x{target[1]}, "
          f"red px left = {red_left} -> {dst.name}")
    return dst


# Matches the oval <svg class="placeholder" ...>...</svg> block on the Country - Map
# front only (the Flag card has its own, differently-shaped placeholder).
_PLACEHOLDER_RE = re.compile(r'<svg\s+class="placeholder".*?</svg>', re.DOTALL)
_IMG_TAG = f'<img src="{BASE_NAME}" />'


def patch_country_map_front(note_models: list) -> int:
    """Swap the oval placeholder for the blank world map on the Country - Map front.

    Idempotent: re-running finds nothing to replace and returns 0.
    """
    n = 0
    for model in note_models:
        for tmpl in model.get("tmpls", []):
            if tmpl.get("name") != "Country - Map":
                continue
            new_q, count = _PLACEHOLDER_RE.subn(_IMG_TAG, tmpl["qfmt"])
            if count:
                tmpl["qfmt"] = new_q
                n += count
    return n


def reorder_templates(note_models: list) -> int:
    """Reorder each model's templates into TEMPLATE_ORDER and renumber `ord`.

    Unknown templates (not in TEMPLATE_ORDER) are kept after the known ones in
    their original relative order. Idempotent. Returns the number of models whose
    template sequence actually changed.
    """
    rank = {name: i for i, name in enumerate(TEMPLATE_ORDER)}
    changed = 0
    for model in note_models:
        tmpls = model.get("tmpls", [])
        orig = {id(t): i for i, t in enumerate(tmpls)}
        before = [t["name"] for t in tmpls]
        tmpls.sort(key=lambda t: rank.get(t["name"], len(rank) + orig[id(t)]))
        for i, t in enumerate(tmpls):
            t["ord"] = i
        if [t["name"] for t in tmpls] != before:
            changed += 1
    return changed


def _apply_to_deck(deck_dir: Path) -> None:
    media = deck_dir / "media"
    deck_json = deck_dir / "deck.json"
    if not deck_json.exists():
        print(f"  SKIP {deck_dir.name}: no deck.json (build it first)")
        return
    build_world_base(media)
    deck = json.loads(deck_json.read_text(encoding="utf-8"))
    models = deck.get("note_models", [])
    patched = patch_country_map_front(models)
    reordered = reorder_templates(models)
    deck_json.write_text(
        json.dumps(deck, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"  {deck_dir.name}: front patched={patched}, models reordered={reordered}")


def main() -> None:
    for d in OUT_DIRS:
        _apply_to_deck(d)


if __name__ == "__main__":
    main()
