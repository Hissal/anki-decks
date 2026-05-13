"""Shared helpers for the deck scripts."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TAGS_FILE = REPO_ROOT / "TAGS.md"

EXPECTED_HEADER = ["Hanzi", "Pinyin", "English", "Note", "Audio", "Tags"]
COLUMN_COUNT = len(EXPECTED_HEADER)

TIER_TAGS = {"production-ready", "recognition-ready", "recognition-first"}

DECKS = {
    "core": "Chinese_Core_Conversation.tsv",
    "idioms": "Chinese_Idioms_Proverbs_Classical.tsv",
    "slang": "Chinese_Slang_Dialect_Flavor.tsv",
}


@dataclass
class Row:
    file: Path
    line_no: int  # 1-indexed including header
    hanzi: str
    pinyin: str
    english: str
    note: str
    audio: str
    tags: list[str] = field(default_factory=list)

    @property
    def raw_tags(self) -> str:
        return " ".join(self.tags)


def deck_paths() -> list[Path]:
    return sorted(REPO_ROOT.glob("*.tsv"))


def parse_tsv(path: Path) -> tuple[list[str], list[Row]]:
    """Return (header, rows). Raises ValueError on header mismatch.

    `utf-8-sig` strips a leading BOM if present — some editors save TSVs that
    way and we don't want the BOM to corrupt the first header field.
    """
    text = path.read_text(encoding="utf-8-sig")
    lines = text.split("\n")
    # Trailing newline produces empty last line — drop it.
    if lines and lines[-1] == "":
        lines.pop()

    if not lines:
        raise ValueError(f"{path.name}: file is empty")

    header = lines[0].split("\t")
    if header != EXPECTED_HEADER:
        raise ValueError(
            f"{path.name}: header mismatch. expected {EXPECTED_HEADER}, got {header}"
        )

    rows: list[Row] = []
    for i, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        fields = line.split("\t")
        # Pad missing trailing fields with empty strings so short rows still parse;
        # the validator will report column-count problems separately.
        while len(fields) < COLUMN_COUNT:
            fields.append("")
        rows.append(
            Row(
                file=path,
                line_no=i,
                hanzi=fields[0],
                pinyin=fields[1],
                english=fields[2],
                note=fields[3],
                audio=fields[4],
                tags=[t for t in fields[5].split(" ") if t],
            )
        )
    return header, rows


def load_allowed_tags() -> set[str]:
    """Read TAGS.md and pull tags out of inline-code backticks in tables."""
    if not TAGS_FILE.exists():
        return set()
    text = TAGS_FILE.read_text(encoding="utf-8")
    return set(re.findall(r"`([a-z][a-z0-9-]*)`", text))


HAN_RE = re.compile(r"[㐀-䶿一-鿿]")
ASCII_LETTER_RE = re.compile(r"[A-Za-z]")
DIGIT_TONE_RE = re.compile(r"[a-zü][1-5]")


def has_han(s: str) -> bool:
    return bool(HAN_RE.search(s))


def has_ascii_letter(s: str) -> bool:
    return bool(ASCII_LETTER_RE.search(s))


def looks_like_digit_pinyin(s: str) -> bool:
    return bool(DIGIT_TONE_RE.search(s.lower()))


def append_row(path: Path, fields: list[str]) -> None:
    """Append one row to a TSV. Each field has tabs/newlines stripped."""
    if len(fields) != COLUMN_COUNT:
        raise ValueError(f"expected {COLUMN_COUNT} fields, got {len(fields)}")
    cleaned = [f.replace("\t", " ").replace("\r", "").replace("\n", " ") for f in fields]
    line = "\t".join(cleaned)
    # Ensure file ends with newline before appending.
    if path.exists():
        existing = path.read_bytes()
        if existing and not existing.endswith(b"\n"):
            with path.open("ab") as f:
                f.write(b"\n")
    with path.open("a", encoding="utf-8", newline="") as f:
        f.write(line + "\n")


def stderr(msg: str) -> None:
    print(msg, file=sys.stderr)
