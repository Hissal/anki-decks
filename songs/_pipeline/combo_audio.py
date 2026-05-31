"""Pre-bake block-cloze combo mp3 files.

For each (block, blanked-line-slot) pair we produce one mp3:
  <slug>_block_<BB>_c<K>.mp3
where BB = block number (2-digit) and K = 1-based slot within the block.

The combo content = concatenation of the block's line clips, with the
blanked slot replaced by silence of the same duration as the clip it
displaced. That keeps the song's rhythm intact while the listener tries
to recall the missing line.

Concat uses ffmpeg's concat demuxer; silence is generated on the fly via
`anullsrc` for each unique duration we need.
"""
from __future__ import annotations
import argparse, subprocess, sys, tempfile
from pathlib import Path

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def probe_duration(ffprobe: str, path: Path) -> float:
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def make_silence(ffmpeg: str, duration: float, out_path: Path):
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error",
         "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
         "-t", f"{duration:.3f}",
         "-c:a", "libmp3lame", "-b:a", "128k",
         str(out_path)],
        check=True,
    )


def concat(ffmpeg: str, files: list[Path], out_path: Path):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_path = Path(f.name)
        for p in files:
            # ffmpeg concat list format: file '<absolute path>'. Concat demuxer
            # resolves relative paths against the list file's own directory,
            # which is /tmp here — so use absolute paths.
            f.write(f"file '{p.resolve().as_posix()}'\n")
    try:
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error",
             "-f", "concat", "-safe", "0",
             "-i", str(list_path),
             "-c:a", "libmp3lame", "-b:a", "128k",
             str(out_path)],
            check=True,
        )
    finally:
        list_path.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", required=True, type=Path)
    ap.add_argument("--media-dir", required=True, type=Path, help="dir holding per-line line clips")
    ap.add_argument("--prefix", required=True, help="e.g. yi_jian_mei (matches line clip filenames)")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--ffprobe", default="ffprobe")
    args = ap.parse_args()

    plan = yaml.safe_load(args.blocks.read_text(encoding="utf-8"))
    silence_cache: dict[str, Path] = {}
    silence_dir = args.media_dir / "_silence"
    silence_dir.mkdir(exist_ok=True)

    total_combos = 0
    for block in plan["blocks"]:
        b_no = block["block_no"]
        line_nos = block["line_nos"]
        line_clips = [args.media_dir / f"{args.prefix}_{n:03d}.mp3" for n in line_nos]
        durations = [probe_duration(args.ffprobe, p) for p in line_clips]

        for k_idx, blank_pos in enumerate(line_nos):
            k = k_idx + 1  # 1-based slot within block
            blank_dur = durations[k_idx]
            # Cache silence file per quantized duration (10ms).
            dur_key = f"{round(blank_dur, 2):.2f}"
            if dur_key not in silence_cache:
                silence_path = silence_dir / f"silence_{dur_key.replace('.', '_')}.mp3"
                if not silence_path.exists():
                    make_silence(args.ffmpeg, float(dur_key), silence_path)
                silence_cache[dur_key] = silence_path
            silence_path = silence_cache[dur_key]

            # Build the concat list for this combo.
            seq: list[Path] = []
            for i, clip in enumerate(line_clips):
                seq.append(silence_path if i == k_idx else clip)

            combo_name = f"{args.prefix}_block_{b_no:02d}_c{k}.mp3"
            combo_path = args.media_dir / combo_name
            concat(args.ffmpeg, seq, combo_path)
            total_combos += 1
            print(f"  block {b_no:02d} slot {k} (line {blank_pos:03d}, silence {blank_dur:.2f}s) -> {combo_name}")

        # Full-block version (no silenced slot) for the card BACK, where the
        # answer line should be audible. Played natively via [sound:] so it
        # routes through Anki's player (and any volume-control addon).
        full_name = f"{args.prefix}_block_{b_no:02d}_full.mp3"
        concat(args.ffmpeg, line_clips, args.media_dir / full_name)
        total_combos += 1
        print(f"  block {b_no:02d} full (no silence) -> {full_name}")

    print(f"wrote {total_combos} combo files to {args.media_dir}/")


if __name__ == "__main__":
    main()
