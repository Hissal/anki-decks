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

    raw_blocks = []
    for group in chunk(indexed, args.block_size):
        raw_blocks.append({
            "line_nos": [row["line_no"] for row in group],
            "hanzi_lines": [row["hanzi"] for row in group],
            "aligned_spans": [
                {"start": row["start"], "end": row["end"]} for row in group
            ],
        })

    # Dedup by content: two blocks with the same tuple of Hanzi lines test
    # the same recall task and produce identical cards. Keep the first
    # occurrence, drop later repeats. Block numbers are assigned post-dedup
    # so they're contiguous (block 01, 02, …) even when chorus blocks were
    # collapsed in the middle of the song.
    seen: dict[tuple, int] = {}
    blocks = []
    skipped: list[tuple[int, int]] = []  # (original_idx, first_seen_block_no)
    for orig_idx, b in enumerate(raw_blocks, 1):
        key = tuple(b["hanzi_lines"])
        if key in seen:
            skipped.append((orig_idx, seen[key]))
            continue
        b_no = len(blocks) + 1
        seen[key] = b_no
        blocks.append({"block_no": b_no, **b})

    plan = {"song_slug": args.song_slug, "block_size": args.block_size, "blocks": blocks}
    args.out.write_text(yaml.safe_dump(plan, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")

    print(f"wrote {len(blocks)} blocks -> {args.out}")
    for b in blocks:
        line_nos = ", ".join(str(n) for n in b["line_nos"])
        print(f"  block {b['block_no']:02d}: lines [{line_nos}]")
    if skipped:
        print(f"  dedup skipped {len(skipped)} block(s) with content matching earlier blocks:")
        for orig, first in skipped:
            print(f"    raw-position {orig:02d} duplicates block {first:02d}")


if __name__ == "__main__":
    main()
