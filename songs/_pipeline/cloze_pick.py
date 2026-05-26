"""Auto-suggest cloze candidates per line and emit a YAML plan for review.

Strategy
--------
1. Segment each Hanzi line with `jieba.posseg` (word + POS tag).
2. Filter out function words (particles, pronouns, conjunctions, very
   common single chars) — those make boring clozes.
3. Score remaining words: prefer multi-char (compound) words, prefer
   content POS tags (noun / verb / adjective / verbal-noun / state).
4. Pick top N (default 2) candidates per line.
5. Emit YAML with both `suggested_clozes` (auto pick) and
   `selected_clozes` (initialized = suggested, user edits before next
   pipeline step).

The selection is intentionally loose — songs are short and the goal is to
amplify the "fun" words, not to be exhaustive. User review is expected.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Re-encode stdout to UTF-8 on Windows so CJK chars in progress prints
# don't crash the run.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import jieba.posseg as pseg
import yaml


# Very-high-frequency single chars that almost never make good clozes.
STOP_CHARS = set("的一不是了在有我你他她它这那个们也都和与又就只还能会要可以没来去过之而但或又啊呀呢吗吧哦嗯啦的就把被让向于于")

# jieba POS tags worth clozing (content words).
CONTENT_POS = {
    "n",    # noun
    "ns",   # place name (kept; could be content)
    "nz",   # other proper noun
    "v",    # verb
    "vn",   # verbal noun
    "a",    # adjective
    "an",   # adjective-noun
    "ad",   # adverb-from-adjective
    "i",    # idiom
    "l",    # set phrase
    "z",    # state word
    "ag",   # adjective morpheme
    "vg",   # verb morpheme
    "ng",   # noun morpheme
}

# Tags we always reject — they're never the cloze target we want.
REJECT_POS = {
    "u",    # auxiliary (的, 了, 地…)
    "p",    # preposition
    "c",    # conjunction
    "r",    # pronoun
    "y",    # modal particle
    "w",    # punctuation
    "x",    # non-CJK
    "m",    # number (e.g. 一, 万) — keep? in songs often poetic. Skip for now.
    "q",    # measure word
    "f",    # locality (上, 下…)
    "d",    # adverb (too generic for cloze)
}


def score_word(word: str, pos: str) -> float:
    """Higher = better cloze candidate."""
    if pos in REJECT_POS:
        return -1
    if len(word) == 1 and word in STOP_CHARS:
        return -1
    score = 0.0
    if pos in CONTENT_POS:
        score += 2.0
    if len(word) >= 2:
        score += 2.0
    if len(word) >= 3:
        score += 1.0
    # Mild penalty for being a single common char.
    if len(word) == 1:
        score -= 0.5
    return score


def pick_for_line(line: str, top_n: int = 2) -> list[dict]:
    """Return list of candidate dicts ordered by suggestion priority."""
    candidates: list[tuple[float, str, str]] = []
    for tok in pseg.cut(line):
        s = score_word(tok.word, tok.flag)
        if s <= 0:
            continue
        candidates.append((s, tok.word, tok.flag))
    # Sort by score desc, but preserve first-appearance order on ties.
    candidates.sort(key=lambda t: -t[0])
    picks: list[dict] = []
    seen: set[str] = set()
    for score, word, pos in candidates:
        if word in seen:
            continue
        seen.add(word)
        picks.append({"word": word, "pos": pos, "score": round(score, 1)})
        if len(picks) >= top_n:
            break
    return picks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lyrics", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--song-slug", required=True)
    ap.add_argument("--block-size", type=int, default=4)
    ap.add_argument("--top-n", type=int, default=2, help="max cloze suggestions per line")
    args = ap.parse_args()

    lines = [ln.strip() for ln in args.lyrics.read_text(encoding="utf-8").splitlines() if ln.strip()]
    plan_lines: list[dict] = []
    for i, line in enumerate(lines, 1):
        picks = pick_for_line(line, top_n=args.top_n)
        plan_lines.append({
            "line_no": i,
            "hanzi": line,
            "suggested_clozes": [p["word"] for p in picks],
            "selected_clozes": [p["word"] for p in picks],
            "_debug": [f"{p['word']} ({p['pos']}, s={p['score']})" for p in picks],
        })

    plan = {
        "song_slug": args.song_slug,
        "block_size": args.block_size,
        "lines": plan_lines,
    }
    args.out.write_text(
        yaml.safe_dump(plan, allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8",
    )
    total = sum(len(l["suggested_clozes"]) for l in plan_lines)
    print(f"wrote {len(plan_lines)} lines, {total} cloze suggestions -> {args.out}")
    print()
    print("Suggestions (review + edit `selected_clozes` in the YAML):")
    for l in plan_lines:
        words = ", ".join(l["suggested_clozes"]) or "(none)"
        print(f"  {l['line_no']:02d}: {l['hanzi']:<20s}  → {words}")


if __name__ == "__main__":
    main()
