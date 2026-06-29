"""Convert traditional Chinese lyrics to simplified.

Uses opencc (t2s) then applies a small fixup table for characters opencc's
default dict leaves alone but the project prefers in the modern simplified
form (e.g. 翦 → 剪).
"""
from __future__ import annotations
import argparse
from pathlib import Path

from opencc import OpenCC


EXTRA_FIXUPS = {
    "翦": "剪",  # opencc t2s leaves 翦 alone (it's a valid char), but the
                 #  modern simplified rendering of 一翦梅 is 一剪梅.
    "痺": "痹",  # opencc t2s leaves the 痺 variant alone; modern simplified
                 #  of 麻痺 (numbness) is 麻痹.
}


def convert(text: str) -> str:
    out = OpenCC("t2s").convert(text)
    for trad, simp in EXTRA_FIXUPS.items():
        out = out.replace(trad, simp)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    src = args.inp.read_text(encoding="utf-8")
    args.out.write_text(convert(src), encoding="utf-8")
    print(f"converted {args.inp} -> {args.out} ({len(src.splitlines())} lines)")


if __name__ == "__main__":
    main()
