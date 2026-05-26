"""Force-align Hanzi lyrics to audio via stable-ts (Whisper-based).

Inputs:
  audio: path to mp3
  lines: list of Hanzi lines (already in simplified)
Output:
  list of {line, start, end} dicts, written as aligned.json
"""
from __future__ import annotations
import json, sys, argparse
from pathlib import Path

import stable_whisper


def align(audio_path: Path, lines: list[str], model_name: str = "small") -> list[dict]:
    model = stable_whisper.load_model(model_name)
    text = "\n".join(lines)
    result = model.align(
        str(audio_path),
        text,
        language="zh",
        original_split=True,
    )
    out: list[dict] = []
    for seg, line in zip(result.segments, lines):
        out.append({"line": line, "start": round(seg.start, 3), "end": round(seg.end, 3)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, type=Path)
    ap.add_argument("--lyrics", required=True, type=Path, help="UTF-8 text, one line per row")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="small")
    args = ap.parse_args()

    lines = [ln.strip() for ln in args.lyrics.read_text(encoding="utf-8").splitlines() if ln.strip()]
    aligned = align(args.audio, lines, args.model)
    args.out.write_text(json.dumps(aligned, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(aligned)} aligned lines -> {args.out}")


if __name__ == "__main__":
    main()
