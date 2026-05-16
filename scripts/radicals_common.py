"""Shared helpers for the Kangxi-radicals deck.

Separate from common.py (word decks) and components_common.py (phonetic
components) because each lives in its own ontology with its own schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from common import REPO_ROOT, HAN_RE

RADICALS_DECK_FILE = "Chinese_Kangxi_Radicals.tsv"
RADICALS_DECK_PATH = REPO_ROOT / RADICALS_DECK_FILE

# 15-column schema. Variants are split into named slots so Anki card templates
# can conditionally generate one card per primary variant.
RADICALS_HEADER = [
    "Key",                # `<radical>:<numeric-pinyin>` — unique first field
    "Radical",            # canonical (simplified) radical character
    "Variant1",           # primary positional variant (e.g. 忄 for 心)
    "Variant2",           # secondary primary variant (e.g. ⺗ for 心)
    "ReferenceVariants",  # remaining variants joined with `,` — shown for reference but no own card
    "Pinyin",             # tone-marked
    "Meaning",
    "MemberChars",        # curated example chars where this radical is the semantic head
    "Productivity",       # HanziCraft "appears as a component in N chars" — total count
    "Frequency",          # HanziCraft frequency rank for the radical standalone (often empty)
    "Decomposition",      # `once:<a>+<b>;radical:<r>` — radical's own breakdown
    "MemberDecomp",       # `海=氵+每|河=氵+可|湖=氵+古` — per-member-char once-level decomp
    "Note",
    "Link",               # HanziCraft URL for the radical + its member chars
    "Tags",
]
RADICALS_COLUMN_COUNT = len(RADICALS_HEADER)

RADICALS_EXPECTED_DIRECTIVES = {
    "separator": "tab",
    "html": "true",
    "tags column": str(RADICALS_COLUMN_COUNT),
}


@dataclass
class RadicalRow:
    file: Path
    line_no: int
    key: str
    radical: str
    variant1: str
    variant2: str
    reference_variants: str
    pinyin: str
    meaning: str
    member_chars: str
    productivity: str
    frequency: str
    decomposition: str
    member_decomp: str
    note: str
    link: str
    tags: list[str] = field(default_factory=list)


def parse_radicals_tsv(path: Path) -> tuple[list[str], list[RadicalRow]]:
    """Parse the Kangxi-radicals TSV. Raises ValueError on header mismatch."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise ValueError(f"{path.name}: file is empty")

    header: list[str] | None = None
    directives: dict[str, str] = {}
    rows: list[RadicalRow] = []

    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if line.startswith("#"):
            key, sep, val = line[1:].partition(":")
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
            raise ValueError(f"{path.name}:{i}: data row before #columns directive")
        fields = line.split("\t")
        while len(fields) < RADICALS_COLUMN_COUNT:
            fields.append("")
        rows.append(
            RadicalRow(
                file=path,
                line_no=i,
                key=fields[0],
                radical=fields[1],
                variant1=fields[2],
                variant2=fields[3],
                reference_variants=fields[4],
                pinyin=fields[5],
                meaning=fields[6],
                member_chars=fields[7],
                productivity=fields[8],
                frequency=fields[9],
                decomposition=fields[10],
                member_decomp=fields[11],
                note=fields[12],
                link=fields[13],
                tags=[t for t in fields[14].split(" ") if t],
            )
        )

    if header is None:
        raise ValueError(f"{path.name}: missing #columns directive")
    if header != RADICALS_HEADER:
        raise ValueError(
            f"{path.name}: #columns mismatch. expected {RADICALS_HEADER}, got {header}"
        )
    for k, want in RADICALS_EXPECTED_DIRECTIVES.items():
        got = directives.get(k)
        if got != want:
            raise ValueError(
                f"{path.name}: directive '#{k}' expected {want!r}, got {got!r}"
            )

    return header, rows


__all__ = [
    "RADICALS_DECK_FILE",
    "RADICALS_DECK_PATH",
    "RADICALS_HEADER",
    "RADICALS_COLUMN_COUNT",
    "RADICALS_EXPECTED_DIRECTIVES",
    "RadicalRow",
    "parse_radicals_tsv",
    "HAN_RE",
]
