"""Slice audio.mp3 into per-line clips using aligned.json."""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path


def slice_audio(
    audio: Path,
    aligned: list[dict],
    out_dir: Path,
    prefix: str,
    ffmpeg: str,
    pad_head: float = 0.15,
    pad_tail: float = 1.50,
):
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for i, row in enumerate(aligned, 1):
        next_start = aligned[i]["start"] if i < len(aligned) else None
        start = max(0.0, row["start"] - pad_head)
        end = row["end"] + pad_tail
        if next_start is not None:
            # Never bleed into the next line; leave a 50ms cushion.
            end = min(end, next_start - 0.05)
        end = max(end, row["end"])  # never shorter than the aligned span itself
        dur = end - start
        fname = f"{prefix}_{i:03d}.mp3"
        out_path = out_dir / fname
        subprocess.run([
            ffmpeg, "-y", "-loglevel", "error",
            "-ss", f"{start:.3f}",
            "-t", f"{dur:.3f}",
            "-i", str(audio),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out_path),
        ], check=True)
        files.append(fname)
        print(f"  {fname}  {start:.2f} -> {end:.2f}  ({dur:.2f}s)")
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, type=Path)
    ap.add_argument("--aligned", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--pad-head", type=float, default=0.15, help="seconds of audio before line start")
    ap.add_argument("--pad-tail", type=float, default=1.50, help="max seconds of audio after line end; auto-capped to next_line.start - 0.05 to avoid overlap")
    args = ap.parse_args()
    aligned = json.loads(args.aligned.read_text(encoding="utf-8"))
    slice_audio(args.audio, aligned, args.out_dir, args.prefix, args.ffmpeg, args.pad_head, args.pad_tail)


if __name__ == "__main__":
    main()
