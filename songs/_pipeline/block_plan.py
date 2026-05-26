"""Chunk lyric lines into N-line blocks for SongBlock cloze cards.

Default: fixed chunks of `--block-size` (e.g. 4). User can edit blocks.yaml
afterward to split / merge / re-size blocks per song musical structure.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aligned", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--song-slug", required=True)
    ap.add_argument("--block-size", type=int, default=4)
    args = ap.parse_args()

    aligned = json.loads(args.aligned.read_text(encoding="utf-8"))
    # Augment lines with a 1-based line_no for clarity (matches everything else).
    indexed = [
        {"line_no": i, "hanzi": row["line"], "start": row["start"], "end": row["end"]}
        for i, row in enumerate(aligned, 1)
    ]

    blocks = []
    for b_no, group in enumerate(chunk(indexed, args.block_size), 1):
        blocks.append({
            "block_no": b_no,
            "line_nos": [row["line_no"] for row in group],
            "hanzi_lines": [row["hanzi"] for row in group],
            # Aligned spans (without padding) — combo_audio.py uses these as a
            # baseline; it derives actual clip duration from the on-disk mp3.
            "aligned_spans": [
                {"start": row["start"], "end": row["end"]} for row in group
            ],
        })

    plan = {"song_slug": args.song_slug, "block_size": args.block_size, "blocks": blocks}
    args.out.write_text(yaml.safe_dump(plan, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")

    print(f"wrote {len(blocks)} blocks -> {args.out}")
    for b in blocks:
        line_nos = ", ".join(str(n) for n in b["line_nos"])
        print(f"  block {b['block_no']:02d}: lines [{line_nos}]")


if __name__ == "__main__":
    main()
