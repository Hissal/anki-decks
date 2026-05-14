#!/usr/bin/env python3
"""Populate the `Link` column with chineseidioms.com URLs.

Three sources on chineseidioms.com:
  - /blog/<pinyin>   — chengyu / proverbs / classical (algorithmic from Pinyin)
  - /slang/<slug>    — internet slang (slugs are inconsistent → lookup table)
  - /phrases/<slug>  — everyday phrases (mostly hyphenated pinyin, with a few
                       quirks → lookup table)

For the idioms deck the URL is derived from the per-character Pinyin column:
strip tones, drop punctuation tokens, lowercase, join with `-`. For the other
two decks the script checks each row's Hanzi against a curated lookup taken
straight from the site's listing pages. Rows whose existing Link is non-empty
are never overwritten.

Rows that get no chineseidioms.com match fall back to an MDBG dictionary
lookup URL (https://www.mdbg.net/chinese/dictionary?wdqb=<hanzi>) when run
with `--mdbg-fallback`. The MDBG URL is algorithmic and covers any hanzi.

Usage:
  python scripts/find_site_links.py                              # dry-run
  python scripts/find_site_links.py --apply                      # write
  python scripts/find_site_links.py --apply --mdbg-fallback      # write +
                                                                   fallback
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.chineseidioms.com"
MDBG = "https://www.mdbg.net/chinese/dictionary?wdqb="

IDIOMS_FILE = "Chinese_Idioms_Proverbs_Classical.tsv"
SLANG_FILE = "Chinese_Slang_Dialect_Flavor.tsv"
CORE_FILE = "Chinese_Core_Conversation.tsv"

# /slang/<slug> — taken from a manual sweep of https://www.chineseidioms.com/slang
# (slugs are not derivable from pinyin: e.g. 割韭菜 → gao-ji, 老六 → lao-liu-bi).
SLANG_MAP: dict[str, str] = {
    "学霸": "/slang/xue-ba",
    "牛逼": "/slang/niu",
}

# /phrases/<slug> — taken from a manual sweep of https://www.chineseidioms.com/phrases
PHRASES_MAP: dict[str, str] = {
    "干杯": "/phrases/gan-bei",
    "算了": "/phrases/suan-le-phrase",
    "加班": "/phrases/jia-ban",
    "开会": "/phrases/kai-hui",
    "加油": "/phrases/jia-you",
    "慢慢来": "/phrases/man-man-lai",
    "改天吧": "/phrases/gai-tian-ba",
    "看情况": "/phrases/kan-qing-kuang",
    "没想到": "/phrases/mei-xiang-dao",
    "有道理": "/phrases/you-dao-li",
    "差不多": "/phrases/cha-bu-duo",
    "习惯了": "/phrases/xi-guan-le",
    "怎么办": "/phrases/zen-me-ban",
    "搞定了": "/phrases/gao-ding-le",
    "来不及了": "/phrases/lai-bu-ji-le",
    "无聊": "/phrases/wu-liao",
    "辛苦了": "/phrases/xin-ku-le",
    "不舒服": "/phrases/bu-shu-fu",
    "帮帮我": "/phrases/bang-bang-wo",
    "累死了": "/phrases/lei-si-le",
    "烦死了": "/phrases/fan-si-le",
}

# Cross-deck: Core deck rows that happen to be documented on /slang.
CORE_CROSS_SLANG: dict[str, str] = {
    "点赞": "/slang/dian-zan",
}


def strip_tones(s: str) -> str:
    decomposed = unicodedata.normalize("NFD", s)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def derive_idiom_url(pinyin: str) -> str | None:
    """Build /blog/<pinyin-hyphenated-notones>. Drops punctuation tokens."""
    tokens: list[str] = []
    for t in pinyin.split():
        stripped = strip_tones(t).lower()
        if re.fullmatch(r"[a-z]+", stripped):
            tokens.append(stripped)
    if not tokens:
        return None
    return f"/blog/{'-'.join(tokens)}"


def mdbg_url(hanzi: str) -> str:
    return MDBG + urllib.parse.quote(hanzi, safe="")


def process_file(
    path: Path, classify: str, *, mdbg_fallback: bool = False
) -> tuple[list[str], list[tuple[int, str]], list[tuple[int, str]], list[tuple[int, str]]]:
    """Returns (new_lines, applied_site, applied_mdbg, missed) — line/hanzi tuples."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.replace("\r\n", "\n").split("\n")
    trailing_newline = text.endswith("\n")

    new_lines: list[str] = []
    applied_site: list[tuple[int, str]] = []
    applied_mdbg: list[tuple[int, str]] = []
    missed: list[tuple[int, str]] = []

    for i, line in enumerate(lines, start=1):
        if not line or line.startswith("#"):
            new_lines.append(line)
            continue
        fields = line.split("\t")
        if len(fields) < 8:
            new_lines.append(line)
            continue

        hanzi = fields[0]
        pinyin = fields[1]
        link = fields[6]

        if link.strip():
            # Never overwrite a user-set link.
            new_lines.append(line)
            continue

        path_part: str | None = None
        if classify == "idioms":
            path_part = derive_idiom_url(pinyin)
        elif classify == "slang":
            path_part = SLANG_MAP.get(hanzi)
        elif classify == "core":
            path_part = PHRASES_MAP.get(hanzi) or CORE_CROSS_SLANG.get(hanzi)

        if path_part:
            fields[6] = SITE + path_part
            new_lines.append("\t".join(fields))
            applied_site.append((i, hanzi))
        elif mdbg_fallback:
            fields[6] = mdbg_url(hanzi)
            new_lines.append("\t".join(fields))
            applied_mdbg.append((i, hanzi))
        else:
            new_lines.append(line)
            missed.append((i, hanzi))

    if trailing_newline and (not new_lines or new_lines[-1] != ""):
        new_lines.append("")

    return new_lines, applied_site, applied_mdbg, missed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes to disk")
    ap.add_argument(
        "--mdbg-fallback",
        action="store_true",
        help="for rows with no chineseidioms.com match, set Link to an MDBG "
        "dictionary lookup URL",
    )
    args = ap.parse_args()

    plan = [
        (IDIOMS_FILE, "idioms"),
        (SLANG_FILE, "slang"),
        (CORE_FILE, "core"),
    ]

    for filename, classify in plan:
        path = REPO_ROOT / filename
        if not path.exists():
            print(f"skip {filename}: not found", file=sys.stderr)
            continue
        new_lines, applied_site, applied_mdbg, missed = process_file(
            path, classify, mdbg_fallback=args.mdbg_fallback
        )
        print(f"\n=== {filename} ({classify}) ===")
        print(f"  chineseidioms.com links: {len(applied_site)}")
        for ln, hz in applied_site[:5]:
            print(f"    {filename}:{ln}  {hz}")
        if len(applied_site) > 5:
            print(f"    ... +{len(applied_site) - 5} more")
        if args.mdbg_fallback:
            print(f"  MDBG fallback links: {len(applied_mdbg)}")
        else:
            print(f"  unmatched: {len(missed)} rows")
        if args.apply and (applied_site or applied_mdbg):
            path.write_text("\n".join(new_lines), encoding="utf-8", newline="")
            print(f"  -> wrote {filename}")

    if not args.apply:
        print("\ndry-run only. re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
