#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reconstruct the un-highlighted base map for the Chinese geography deck.

Every <Province>.png is the same 500x425 China locator map with exactly one
province filled red. For any given pixel the red highlight appears in at most
ONE of the 33 images; the other 32 show that pixel's normal base colour. So the
per-pixel MEDIAN across all images (N=33 is odd -> the median is a real, present
value, and the >=17/33 base majority always wins) rebuilds the blank map with
pixel-identical projection, borders and colours.

Writes media/_China_base.png. Re-run if the source maps ever change.
"""

import glob
import os
from pathlib import Path

import numpy as np
from PIL import Image

MEDIA = Path(__file__).resolve().parent / "知识__Geography__Chinese_provinces_and_more" / "media"
OUT = MEDIA / "_China_base.png"


def main() -> None:
    files = sorted(
        f for f in glob.glob(str(MEDIA / "*.png"))
        if not os.path.basename(f).startswith("_")
    )
    if not files:
        raise SystemExit("no source PNGs found in " + str(MEDIA))

    stack = np.stack(
        [np.asarray(Image.open(f).convert("RGB"), dtype=np.uint32) for f in files],
        axis=0,
    )  # (N, H, W, 3)

    codes = (stack[..., 0] << 16) | (stack[..., 1] << 8) | stack[..., 2]  # (N, H, W)
    base = np.median(codes, axis=0).astype(np.uint32)  # (H, W), exact for odd N

    out = np.empty(base.shape + (3,), dtype=np.uint8)
    out[..., 0] = (base >> 16) & 0xFF
    out[..., 1] = (base >> 8) & 0xFF
    out[..., 2] = base & 0xFF
    Image.fromarray(out, "RGB").save(OUT)

    # report how much red was removed (sanity)
    red_like = ((stack[..., 0] > 150) & (stack[..., 1] < 100) & (stack[..., 2] < 100))
    print("source maps :", len(files))
    print("canvas      :", out.shape[1], "x", out.shape[0])
    base_red = ((out[..., 0] > 150) & (out[..., 1] < 100) & (out[..., 2] < 100)).sum()
    print("red px in sources (avg/img):", int(red_like.sum() / len(files)))
    print("red px left in base map    :", int(base_red))
    print("wrote       :", OUT.name)


if __name__ == "__main__":
    main()
