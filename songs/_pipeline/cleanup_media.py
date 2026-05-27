"""Prune unreferenced audio files from a song's media/ dir.

Use at the end of the per-song pipeline (after build_tsv.py +
build_blocks_tsv.py have emitted their final TSVs). Walks the media/
folder, identifies which clips are actually referenced by either:

  - a SongLine note's `Audio` field (via the Cloze TSV — has lower
    coverage than Basic, both share the same set of unique lines)
  - a SongBlock note's per-line slot (via blocks.yaml `line_nos`)
  - a SongBlock note's pre-baked combo for that block (one combo per
    block × per slot K)

…and deletes everything else. The `_silence/` cache subdir is left
alone — it's regenerable but tiny.

Idempotent: re-running after a clean state is a no-op.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


LINE_RE = re.compile(r"^(?P<prefix>.+)_(?P<n>\d{3})\.mp3$")
COMBO_RE = re.compile(r"^(?P<prefix>.+)_block_(?P<b>\d{2})_c(?P<k>\d+)\.mp3$")


def referenced_files(
    media_dir: Path,
    prefix: str,
    blocks_yaml: Path,
    line_tsv: Path,
) -> set[str]:
    """Return the set of mp3 *filenames* (no path) that must be kept."""
    keep: set[str] = set()

    # Lines referenced by SongLine notes — read from the Cloze TSV's `Audio`
    # column (matches Basic since both share the same unique-line set).
    audio_token_re = re.compile(r"\[sound:([^\]]+)\]")
    for ln in line_tsv.read_text(encoding="utf-8").splitlines():
        if not ln or ln.startswith("#"):
            continue
        for m in audio_token_re.finditer(ln):
            keep.add(m.group(1))

    # Lines referenced inside each block + the combo mp3s themselves.
    blocks = yaml.safe_load(blocks_yaml.read_text(encoding="utf-8"))
    for b in blocks["blocks"]:
        b_no = b["block_no"]
        line_nos = b["line_nos"]
        for n in line_nos:
            keep.add(f"{prefix}_{int(n):03d}.mp3")
        for k_idx in range(len(line_nos)):
            keep.add(f"{prefix}_block_{b_no:02d}_c{k_idx + 1}.mp3")

    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--media-dir", required=True, type=Path)
    ap.add_argument("--prefix", required=True, help="song slug, e.g. ganma")
    ap.add_argument("--blocks", required=True, type=Path, help="blocks.yaml")
    ap.add_argument("--line-tsv", required=True, type=Path,
                    help="any of the Lines TSVs (Basic or Cloze — same audio set)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    keep = referenced_files(args.media_dir, args.prefix, args.blocks, args.line_tsv)
    print(f"  referenced: {len(keep)} files")

    to_delete: list[Path] = []
    for p in sorted(args.media_dir.glob("*.mp3")):
        if p.name in keep:
            continue
        # Sanity: only touch files matching our prefix's expected patterns —
        # never delete something unrelated that happened to live here.
        m_line = LINE_RE.match(p.name)
        m_combo = COMBO_RE.match(p.name)
        if not m_line and not m_combo:
            continue
        if m_line and m_line.group("prefix") != args.prefix:
            continue
        if m_combo and m_combo.group("prefix") != args.prefix:
            continue
        to_delete.append(p)

    if not to_delete:
        print("  nothing to prune.")
        return

    action = "would delete" if args.dry_run else "deleted"
    for p in to_delete:
        if not args.dry_run:
            p.unlink()
        print(f"    {action}: {p.name}")
    print(f"  {action} {len(to_delete)} file(s)")


if __name__ == "__main__":
    main()
