"""Shared helpers for the deck scripts."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TAGS_FILE = REPO_ROOT / "TAGS.md"

EXPECTED_HEADER = [
    "Hanzi",
    "Pinyin",
    "English",
    "Breakdown",
    "Examples",
    "Note",
    "Link",
    "Tags",
]
COLUMN_COUNT = len(EXPECTED_HEADER)

# Anki TSV directive lines, prepended to every deck file. The #columns directive
# doubles as the header — there is no separate header row.
EXPECTED_DIRECTIVES = {
    "separator": "tab",
    "html": "true",
    "tags column": str(COLUMN_COUNT),
}

TIER_TAGS = {"production-ready", "recognition-ready", "recognition-first"}

DECKS = {
    "core": "Chinese_Core_Conversation.tsv",
    "idioms": "Chinese_Idioms_Proverbs_Classical.tsv",
    "slang": "Chinese_Slang_Dialect_Flavor.tsv",
}


@dataclass
class Row:
    file: Path
    line_no: int  # 1-indexed file line number
    hanzi: str
    pinyin: str
    english: str
    breakdown: str
    examples: str
    note: str
    link: str
    tags: list[str] = field(default_factory=list)

    @property
    def raw_tags(self) -> str:
        return " ".join(self.tags)


def deck_paths() -> list[Path]:
    return sorted(REPO_ROOT.glob("*.tsv"))


def parse_tsv(path: Path) -> tuple[list[str], list[Row]]:
    """Return (header, rows). Raises ValueError on header / directive mismatch.

    File layout: Anki TSV directives (lines starting with `#`) followed by data
    rows. The `#columns:` directive doubles as the header — no separate header
    row. `utf-8-sig` strips a leading BOM if present.
    """
    text = path.read_text(encoding="utf-8-sig")
    # Normalize CRLF so line numbers stay accurate either way.
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    if not lines:
        raise ValueError(f"{path.name}: file is empty")

    header: list[str] | None = None
    directives: dict[str, str] = {}
    rows: list[Row] = []

    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if line.startswith("#"):
            body = line[1:]
            key, sep, val = body.partition(":")
            if not sep:
                raise ValueError(f"{path.name}:{i}: malformed directive {line!r}")
            key = key.strip().lower()
            val = val.strip()
            if key == "columns":
                header = val.split("\t")
            else:
                directives[key] = val
            continue
        if header is None:
            raise ValueError(
                f"{path.name}:{i}: data row before #columns directive"
            )
        fields = line.split("\t")
        # Pad missing trailing fields with empty strings; validator reports width
        # problems separately.
        while len(fields) < COLUMN_COUNT:
            fields.append("")
        rows.append(
            Row(
                file=path,
                line_no=i,
                hanzi=fields[0],
                pinyin=fields[1],
                english=fields[2],
                breakdown=fields[3],
                examples=fields[4],
                note=fields[5],
                link=fields[6],
                tags=[t for t in fields[7].split(" ") if t],
            )
        )

    if header is None:
        raise ValueError(f"{path.name}: missing #columns directive")
    if header != EXPECTED_HEADER:
        raise ValueError(
            f"{path.name}: #columns mismatch. expected {EXPECTED_HEADER}, got {header}"
        )
    for k, want in EXPECTED_DIRECTIVES.items():
        got = directives.get(k)
        if got != want:
            raise ValueError(
                f"{path.name}: directive '#{k}' expected {want!r}, got {got!r}"
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
