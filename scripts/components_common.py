"""Shared helpers for the phonetic-components deck.

Separate from common.py because the schema differs from the word decks. The
file lives at the repo root alongside the word-deck TSVs, but the existing
word-deck tooling (validate.py, index.py via deck_paths()) intentionally
skips it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from common import REPO_ROOT, HAN_RE  # re-use shared regexes

COMPONENT_DECK_FILE = "Chinese_Phonetic_Components.tsv"
COMPONENT_DECK_PATH = REPO_ROOT / COMPONENT_DECK_FILE

COMPONENT_HEADER = [
    "Key",           # `<component>:<numeric-pinyin>` — Anki note's unique first field
    "Component",     # the lone phonetic, shown on card fronts/backs
    "Pinyin",        # tone-marked
    "Meaning",
    "MemberChars",
    "Reliability",   # "X/Y" or "X/Y (ignoring tone)" — sound-match within member chars
    "Productivity",  # HanziCraft's "appears as a component in N characters" — total count
    "Frequency",     # HanziCraft's frequency rank (e.g. "118" for the 118th most frequent character)
    "Decomposition", # `once:<a>+<b>;radical:<r>` — component's own top-level + radical breakdown
    "CrossRefs",     # other readings of the same component: `qiào / 俏峭鞘诮 · shāo / 稍梢捎艄筲`
    "Note",
    "Link",          # HanziCraft URL for the component + member chars
    "Audio",
    "Tags",
]
COMPONENT_COLUMN_COUNT = len(COMPONENT_HEADER)

COMPONENT_EXPECTED_DIRECTIVES = {
    "separator": "tab",
    "html": "true",
    "tags column": str(COMPONENT_COLUMN_COUNT),
}


@dataclass
class ComponentRow:
    file: Path
    line_no: int
    key: str
    component: str
    pinyin: str
    meaning: str
    member_chars: str
    reliability: str
    productivity: str
    frequency: str
    decomposition: str
    cross_refs: str
    note: str
    link: str
    audio: str
    tags: list[str] = field(default_factory=list)


def parse_component_tsv(path: Path) -> tuple[list[str], list[ComponentRow]]:
    """Parse the phonetic-components TSV. Raises ValueError on header mismatch."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    if not lines:
        raise ValueError(f"{path.name}: file is empty")

    header: list[str] | None = None
    directives: dict[str, str] = {}
    rows: list[ComponentRow] = []

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
        while len(fields) < COMPONENT_COLUMN_COUNT:
            fields.append("")
        rows.append(
            ComponentRow(
                file=path,
                line_no=i,
                key=fields[0],
                component=fields[1],
                pinyin=fields[2],
                meaning=fields[3],
                member_chars=fields[4],
                reliability=fields[5],
                productivity=fields[6],
                frequency=fields[7],
                decomposition=fields[8],
                cross_refs=fields[9],
                note=fields[10],
                link=fields[11],
                audio=fields[12],
                tags=[t for t in fields[13].split(" ") if t],
            )
        )

    if header is None:
        raise ValueError(f"{path.name}: missing #columns directive")
    if header != COMPONENT_HEADER:
        raise ValueError(
            f"{path.name}: #columns mismatch. expected {COMPONENT_HEADER}, got {header}"
        )
    for k, want in COMPONENT_EXPECTED_DIRECTIVES.items():
        got = directives.get(k)
        if got != want:
            raise ValueError(
                f"{path.name}: directive '#{k}' expected {want!r}, got {got!r}"
            )

    return header, rows


__all__ = [
    "COMPONENT_DECK_FILE",
    "COMPONENT_DECK_PATH",
    "COMPONENT_HEADER",
    "COMPONENT_COLUMN_COUNT",
    "COMPONENT_EXPECTED_DIRECTIVES",
    "ComponentRow",
    "parse_component_tsv",
    "HAN_RE",
]
