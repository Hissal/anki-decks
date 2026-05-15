#!/usr/bin/env python3
"""Generate Chinese_Phonetic_Components.tsv from the rough HanziCraft-derived
source file.

One-shot, NOT idempotent. Overwrites the output TSV on every run.

Source: a 10-column TSV that's been edited by hand and has rough edges —
numeric pinyin (li3), CSV-quoted multi-line cells, misaligned columns on a
couple of rows, inconsistent comment formatting. This script cleans and
normalizes into the 8-column phonetic-components schema.

Usage:
  python scripts/import_phonetic_components.py [--source PATH]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

from common import HAN_RE, REPO_ROOT
from components_common import (
    COMPONENT_DECK_PATH,
    COMPONENT_HEADER,
)

DEFAULT_SOURCE = Path(
    r"C:\Users\hissa\OneDrive\Työpöytä\Selected Notes.txt"
)
DEFAULT_ENRICH = REPO_ROOT / "scripts" / "cache" / "hanzicraft.json"
DEFAULT_CWC = REPO_ROOT / "scripts" / "cache" / "component_cwc.json"
DEFAULT_CHAR_DATA = REPO_ROOT / "scripts" / "cache" / "char_data.json"
HANZICRAFT_URL = "https://hanzicraft.com/dashboard/character/{}"

SOURCE_COLUMN_COUNT = 10  # source TSV has 10 columns per its directive

# ---------------------------------------------------------------------------
# Pinyin numeric-to-tonemark conversion
# ---------------------------------------------------------------------------

TONE_MARKS: dict[str, list[str]] = {
    "a": ["a", "ā", "á", "ǎ", "à", "a"],
    "e": ["e", "ē", "é", "ě", "è", "e"],
    "i": ["i", "ī", "í", "ǐ", "ì", "i"],
    "o": ["o", "ō", "ó", "ǒ", "ò", "o"],
    "u": ["u", "ū", "ú", "ǔ", "ù", "u"],
    "ü": ["ü", "ǖ", "ǘ", "ǚ", "ǜ", "ü"],
}

PINYIN_RE = re.compile(r"^([a-zü]+?)([1-5])?$")


def numeric_pinyin_to_marks(raw: str) -> str | None:
    """Convert e.g. `gong3` → `gǒng`, `lv3` → `lǚ`. Returns None on parse failure.

    Tone mark placement follows the standard rule: a > e > o, then iu→u, ui→i,
    otherwise the lone vowel. `v` is mapped to `ü`. Tone 5 (neutral) drops the
    digit and leaves no diacritic.
    """
    s = raw.strip().lower().replace("v", "ü")
    if not s:
        return ""
    m = PINYIN_RE.match(s)
    if not m:
        return None
    syllable, tone_str = m.group(1), m.group(2)
    tone = int(tone_str) if tone_str else 5
    if tone == 5 or tone < 1 or tone > 5:
        return syllable
    for vowel in ("a", "e", "o"):
        if vowel in syllable:
            return syllable.replace(vowel, TONE_MARKS[vowel][tone], 1)
    if "iu" in syllable:
        return syllable.replace("u", TONE_MARKS["u"][tone], 1)
    if "ui" in syllable:
        return syllable.replace("i", TONE_MARKS["i"][tone], 1)
    for vowel in ("i", "u", "ü"):
        if vowel in syllable:
            return syllable.replace(vowel, TONE_MARKS[vowel][tone], 1)
    return syllable


# ---------------------------------------------------------------------------
# Comments parsing — split into reliability + note
# ---------------------------------------------------------------------------

RELIABILITY_RE = re.compile(r"^\s*(\d+\s*/\s*\d+)(\s+ignoring\s+tone)?\s*$", re.IGNORECASE)


def parse_comments(raw: str) -> tuple[str, str]:
    """Return (reliability, note). See module docstring for input shape."""
    if not raw:
        return "", ""
    s = raw
    s = re.sub(r"</div\s*>\s*<div[^>]*>", "<br>", s, flags=re.IGNORECASE)
    s = re.sub(r"</?div[^>]*>", "", s, flags=re.IGNORECASE)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"<br\s*/?\s*>", "\n", s, flags=re.IGNORECASE)

    reliabilities: list[str] = []
    notes: list[str] = []
    for token in s.split("\n"):
        t = token.strip()
        if not t:
            continue
        m = RELIABILITY_RE.match(t)
        if m:
            stat = re.sub(r"\s*/\s*", "/", m.group(1))
            label = " (ignoring tone)" if m.group(2) else ""
            reliabilities.append(f"{stat}{label}")
        else:
            notes.append(t)

    reliability = " · ".join(reliabilities)
    note = "<br>".join(notes)
    return reliability, note


# ---------------------------------------------------------------------------
# Row transformation
# ---------------------------------------------------------------------------


HTML_ENTITY_RE = re.compile(r"&(?:nbsp|amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);")


def strip_html_noise(s: str) -> str:
    """Drop HTML entities (`&nbsp;` etc.) and stray tags from a field."""
    s = HTML_ENTITY_RE.sub("", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


def strip_component_from_set(component: str, member_chars: str) -> str:
    """Drop the component itself from MemberChars if it appears there.

    The source set sometimes leads with the component (row 6: 立粒笠莅蒞 where
    立 is the component). Standardize so MemberChars is always derived-chars
    only.
    """
    if not component or not member_chars:
        return member_chars
    return "".join(ch for ch in member_chars if ch != component)


def has_cjk(s: str) -> bool:
    return bool(HAN_RE.search(s))


def detect_misalignment(fields: list[str]) -> tuple[list[str], str | None]:
    """If col 1 (Component slot) has no CJK but col 2 does, treat col 2 as the
    Component and col 1 as a misplaced Meaning. Returns (fixed_fields, warning).
    """
    if len(fields) < 6:
        return fields, None
    col_component = fields[1]
    col_traditional = fields[2]
    if col_component and not has_cjk(col_component) and has_cjk(col_traditional):
        fixed = list(fields)
        # Promote col 2 to Component, demote col 1 into col 5 (Meaning) if
        # empty, otherwise append it to the existing meaning.
        misplaced = fixed[1]
        fixed[1] = fixed[2]
        fixed[2] = ""
        if not fixed[5].strip():
            fixed[5] = misplaced
        else:
            fixed[5] = f"{fixed[5]} / {misplaced}"
        return fixed, (
            f"col-1 had non-CJK {misplaced!r}; promoted col-2 to Component "
            f"and moved {misplaced!r} into Meaning"
        )
    return fields, None


PINYIN_TOKEN_RE = re.compile(r"^[a-zA-Züü]+[1-5]?$", re.IGNORECASE)


def clean_pinyin_field(raw: str) -> tuple[str, list[str]]:
    """Pull a single ASCII pinyin token out of a noisy field.

    Some source rows have things like `圭<br>ya2` in Pinyin — the leading CJK
    references a related "real" phonetic. Returns (best_pinyin_token, extras),
    where extras are non-pinyin scraps to fold into Note.
    """
    if not raw:
        return "", []
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    extras: list[str] = []
    candidate: str | None = None
    for tok in re.split(r"[\s\n]+", text):
        tok = tok.strip()
        if not tok:
            continue
        if PINYIN_TOKEN_RE.match(tok) and not has_cjk(tok):
            if candidate is None:
                candidate = tok
            else:
                extras.append(tok)
        else:
            extras.append(tok)
    return candidate or "", extras


MNEMONIC_RE = re.compile(r"[+]|\s{2,}")
# `-<CJK chars>` → these chars CONTAIN this component but DON'T take this sound (exceptions).
# `+<CJK chars>` → these chars are RELATED in some other way (often visual or structural).
EXCEPTION_HINT_RE = re.compile(r"^\s*-([㐀-鿿]+)\s*$")
RELATED_HINT_RE = re.compile(r"^\s*\+([㐀-鿿]+)\s*$")


def looks_mnemonic(meaning: str) -> bool:
    """Heuristic: source 'meanings' that are HanziCraft mnemonics (e.g.
    'cleats + heart + foreman + crown') vs real glosses ('work', 'skin')."""
    if not meaning:
        return False
    if "+" in meaning:
        return True
    if len(meaning) > 30:
        return True
    return False


def reformat_note_hints(note: str) -> str:
    """Walk a `<br>`-joined Note and expand cryptic `-X` / `+X` hints into
    plain-English labels. Other tokens pass through unchanged."""
    if not note:
        return note
    out: list[str] = []
    for token in note.split("<br>"):
        t = token.strip()
        if not t:
            continue
        m = EXCEPTION_HINT_RE.match(t)
        if m:
            out.append(f"Exceptions (different sound): {m.group(1)}")
            continue
        m = RELATED_HINT_RE.match(t)
        if m:
            out.append(f"Also related: {m.group(1)}")
            continue
        out.append(t)
    return "<br>".join(out)


UNGLYPHABLE = "No glyph available"


def _clean_decomp_parts(parts: list[str]) -> list[str]:
    """Replace HanziCraft's `No glyph available` placeholder with `?`."""
    return ["?" if p == UNGLYPHABLE else p for p in parts]


def build_decomposition(component: str, hc_decomp: dict | None) -> str:
    """Pack the component's own top-level decomposition into a tiny TSV-safe
    string: `once:一+丄;radical:工`. Skips parts that are trivially equal
    to the component itself."""
    if not hc_decomp:
        return ""
    parts: list[str] = []
    once = _clean_decomp_parts(hc_decomp.get("once") or [])
    radical = _clean_decomp_parts(hc_decomp.get("radical") or [])
    if once and not (len(once) == 1 and once[0] == component):
        parts.append("once:" + "+".join(once))
    if radical and not (len(radical) == 1 and radical[0] == component):
        parts.append("radical:" + "+".join(radical))
    return ";".join(parts)


def strip_tone(pinyin: str) -> str:
    """Drop the trailing tone digit from numeric pinyin (gong3 → gong).
    Lowercase the result so a HanziCraft `Gong1` (proper noun marker) compares
    equal to a row's `gong1`."""
    return re.sub(r"\d$", "", (pinyin or "").lower())


def compute_same_syllable_bucket(
    component: str,
    row_pinyin_numeric: str,
    member_chars: str,
    cwc: dict[str, list[str]] | None,
    char_data: dict[str, dict] | None,
) -> str:
    """Walk the full characters-with-this-component list and return chars whose
    pinyin shares this row's syllable but has a different tone (bucket 2)."""
    if not (cwc and char_data):
        return ""
    full = cwc.get(component) or []
    if not full:
        return ""
    target_syllable = strip_tone(row_pinyin_numeric)
    if not target_syllable:
        return ""
    target_full = (row_pinyin_numeric or "").lower()
    in_bucket1 = set(member_chars)
    bucket2: list[str] = []
    for ch in full:
        if ch == component or ch in in_bucket1:
            continue
        data = char_data.get(ch)
        if not data:
            continue
        ch_pinyin = (data.get("pinyin") or "").lower()
        if not ch_pinyin:
            continue
        if ch_pinyin == target_full:
            # Same exact sound — source forgot to curate this one. Treat as
            # bucket-1 for purposes of the count; don't put it in bucket 2.
            continue
        if strip_tone(ch_pinyin) == target_syllable:
            bucket2.append(ch)
    return "".join(bucket2)


def transform_row(
    fields: list[str],
    line_no: int,
    log: list[str],
    enrich: dict[str, dict] | None,
    cwc: dict[str, list[str]] | None,
    char_data: dict[str, dict] | None,
) -> list[str] | None:
    """Map a 10-col source row → 15-col output row. Returns None to skip."""
    while len(fields) < SOURCE_COLUMN_COUNT:
        fields.append("")

    fields, warn = detect_misalignment(fields)
    if warn:
        log.append(f"line {line_no}: {warn}")

    src_set = strip_html_noise(fields[0])
    src_simplified = strip_html_noise(fields[1])
    src_traditional = strip_html_noise(fields[2])
    src_variant = strip_html_noise(fields[3])
    # fields[4] is Image — always empty in source; drop
    src_meaning = strip_html_noise(fields[5])
    src_pinyin_raw = fields[6]
    src_comments = fields[7]
    src_audio = fields[8].strip()
    src_tags = fields[9].strip()

    src_pinyin, pinyin_extras = clean_pinyin_field(src_pinyin_raw)
    if pinyin_extras:
        log.append(
            f"line {line_no}: stripped non-pinyin from Pinyin field for "
            f"{src_simplified!r}: {pinyin_extras!r}"
        )

    if not src_simplified:
        log.append(f"line {line_no}: empty Component column — skipping row")
        return None
    if not has_cjk(src_simplified):
        log.append(
            f"line {line_no}: Component {src_simplified!r} contains no CJK — skipping row"
        )
        return None

    # Component is normally a single CJK char. If multiple (rare in source),
    # keep verbatim — phase 1 doesn't try to be clever.
    component = src_simplified

    pinyin_marks: str
    if not src_pinyin:
        pinyin_marks = ""
        log.append(f"line {line_no}: empty Pinyin for {component!r}")
    else:
        converted = numeric_pinyin_to_marks(src_pinyin)
        if converted is None:
            log.append(
                f"line {line_no}: could not parse Pinyin {src_pinyin!r} "
                f"for {component!r}; keeping raw"
            )
            pinyin_marks = src_pinyin
        else:
            pinyin_marks = converted

    member_chars = strip_component_from_set(component, src_set)

    reliability, note_from_comments = parse_comments(src_comments)

    # HanziCraft enrichment overlay (additive — never touches Pinyin).
    hc = enrich.get(component) if enrich else None
    hc_definition = (hc or {}).get("definition") or ""
    hc_freq_rank = (hc or {}).get("frequency_rank") or ""
    hc_productivity = (hc or {}).get("productivity_count")
    hc_productivity_str = str(hc_productivity) if hc_productivity is not None else ""
    hc_decomp = (hc or {}).get("decomposition")

    meaning_value = src_meaning
    if hc_definition:
        # HanziCraft wins on Meaning when present. Source meanings (often
        # mnemonic-style) are dropped — phase-3A notes pass.
        meaning_value = hc_definition.replace("/", " / ")
    # else: keep src_meaning unchanged

    extras: list[str] = []
    if src_traditional and src_traditional != component:
        extras.append(f"Traditional: {src_traditional}")
    if src_variant:
        extras.append(f"Variant: {src_variant}")
    if pinyin_extras:
        extras.append("See also: " + " ".join(pinyin_extras))
    if note_from_comments:
        extras.append(note_from_comments)
    note = reformat_note_hints("<br>".join(extras))

    decomposition = build_decomposition(component, hc_decomp)

    same_syllable_chars = compute_same_syllable_bucket(
        component=component,
        row_pinyin_numeric=src_pinyin,
        member_chars=member_chars,
        cwc=cwc,
        char_data=char_data,
    )

    # Link: full HanziCraft dashboard URL covering component + all member chars
    # so the destination page shows them together (e.g. /dashboard/character/工巩鞏汞銾).
    link_target = component + member_chars
    link = HANZICRAFT_URL.format(urllib.parse.quote(link_target))

    tags = "phonetic-component"
    if src_tags:
        # Source mostly has nothing here, but preserve anything extra.
        tags = f"{tags} {src_tags.replace(chr(9), ' ').strip()}"

    # The Anki note's first field must be unique per-note. Multiple readings of
    # the same component (e.g. 肖 = xiāo / qiào / shāo) need to coexist, so use
    # `<component>:<numeric-pinyin>` as the Key. Card templates display
    # {{Component}} on the front, not {{Key}}.
    key_pinyin = (
        src_pinyin.lower() if src_pinyin else f"row{line_no}"
    )
    key = f"{component}:{key_pinyin}"

    return [
        key,
        component,
        pinyin_marks,
        meaning_value,
        member_chars,
        same_syllable_chars,
        reliability,
        hc_productivity_str,
        hc_freq_rank,
        decomposition,
        "",          # CrossRefs filled in main() after all rows are known
        note,
        link,
        src_audio,
        tags,
    ]


# ---------------------------------------------------------------------------
# Source reader
# ---------------------------------------------------------------------------


def read_source(path: Path, log: list[str]) -> list[tuple[int, list[str]]]:
    """Read the source TSV. Returns list of (line_no, fields) tuples.

    Uses `csv.reader` so CSV-quoted multi-line cells (the broken rows 179-182,
    297-298, 408-411 etc.) collapse correctly into single logical rows.
    """
    text = path.read_text(encoding="utf-8-sig")
    # Normalize line endings before csv parses, otherwise CR characters leak
    # into quoted cells.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    rows: list[tuple[int, list[str]]] = []
    reader = csv.reader(text.splitlines(keepends=False), delimiter="\t", quotechar='"')
    line_no = 0
    for fields in reader:
        line_no += 1
        if not fields or all(not f.strip() for f in fields):
            continue
        first = fields[0].lstrip()
        if first.startswith("#"):
            continue
        rows.append((line_no, fields))
    log.append(f"read {len(rows)} non-empty, non-directive rows from source")
    return rows


# ---------------------------------------------------------------------------
# TSV writer
# ---------------------------------------------------------------------------


def sanitize_field(s: str) -> str:
    """TSV-safe: no tabs, no raw newlines. Convert internal newlines to <br>."""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    s = s.replace("\t", " ")
    return s


def write_output(rows: list[list[str]], out_path: Path) -> None:
    header_col_count = len(COMPONENT_HEADER)
    header_line = "\t".join(COMPONENT_HEADER)
    lines: list[str] = [
        "#separator:tab",
        "#html:true",
        f"#columns:{header_line}",
        f"#tags column:{header_col_count}",
    ]
    for r in rows:
        if len(r) != header_col_count:
            raise ValueError(f"row has wrong column count: {r!r}")
        lines.append("\t".join(sanitize_field(f) for f in r))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                    help="path to the source notes TSV")
    ap.add_argument("--out", type=Path, default=COMPONENT_DECK_PATH,
                    help="output TSV path")
    ap.add_argument("--enrich", type=Path, default=DEFAULT_ENRICH,
                    help="HanziCraft JSON cache to merge in (optional)")
    ap.add_argument("--no-enrich", action="store_true",
                    help="skip enrichment even if cache file exists")
    ap.add_argument("--cwc", type=Path, default=DEFAULT_CWC,
                    help="per-component characterswithcomponent cache (optional)")
    ap.add_argument("--char-data", type=Path, default=DEFAULT_CHAR_DATA,
                    help="per-character pinyin cache (optional)")
    args = ap.parse_args()

    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 1

    enrich: dict[str, dict] | None = None
    if not args.no_enrich and args.enrich.exists():
        try:
            enrich = json.loads(args.enrich.read_text(encoding="utf-8"))
            print(f"loaded enrichment for {len(enrich)} components from "
                  f"{args.enrich}", file=sys.stderr)
        except Exception as e:
            print(f"warn: failed to load enrich file {args.enrich}: {e}", file=sys.stderr)
            enrich = None
    elif not args.no_enrich:
        print(f"note: enrichment file {args.enrich} not found; phase-1-only output",
              file=sys.stderr)

    cwc: dict[str, list[str]] | None = None
    if args.cwc.exists():
        try:
            cwc = json.loads(args.cwc.read_text(encoding="utf-8"))
            print(f"loaded cwc lists for {len(cwc)} components from {args.cwc}",
                  file=sys.stderr)
        except Exception as e:
            print(f"warn: failed to load cwc file {args.cwc}: {e}", file=sys.stderr)

    char_data: dict[str, dict] | None = None
    if args.char_data.exists():
        try:
            char_data = json.loads(args.char_data.read_text(encoding="utf-8"))
            print(f"loaded char data for {len(char_data)} chars from {args.char_data}",
                  file=sys.stderr)
        except Exception as e:
            print(f"warn: failed to load char-data file {args.char_data}: {e}",
                  file=sys.stderr)

    log: list[str] = []
    src_rows = read_source(args.source, log)

    out_rows: list[list[str]] = []
    seen: dict[str, tuple[int, int]] = {}  # key_field -> (src_line, out_index)
    # Field indices for the 15-col schema:
    #  0=Key, 1=Component, 2=Pinyin, 3=Meaning, 4=MemberChars,
    #  5=SameSyllableChars, 6=Reliability, 7=Productivity, 8=Frequency,
    #  9=Decomposition, 10=CrossRefs, 11=Note, 12=Link, 13=Audio, 14=Tags
    MERGE_COPY_IF_EMPTY = (3, 4, 5, 6, 7, 8, 9, 12, 13)  # don't merge Key/Component/Pinyin/CrossRefs/Note/Tags
    NOTE_IDX = 11

    for line_no, fields in src_rows:
        try:
            row = transform_row(fields, line_no, log, enrich, cwc, char_data)
        except Exception as e:
            log.append(f"line {line_no}: transform error: {e!r}; skipping")
            continue
        if row is None:
            continue
        key_field = row[0]
        if key_field in seen:
            _src_line, out_idx = seen[key_field]
            survivor = out_rows[out_idx]
            merged: list[str] = []
            for i in MERGE_COPY_IF_EMPTY:
                if not survivor[i].strip() and row[i].strip():
                    survivor[i] = row[i]
                    merged.append(COMPONENT_HEADER[i])
            if row[NOTE_IDX].strip():
                if survivor[NOTE_IDX].strip():
                    if row[NOTE_IDX] not in survivor[NOTE_IDX]:
                        survivor[NOTE_IDX] = (
                            survivor[NOTE_IDX] + "<br>" + row[NOTE_IDX]
                        )
                        merged.append(COMPONENT_HEADER[NOTE_IDX] + "(appended)")
                else:
                    survivor[NOTE_IDX] = row[NOTE_IDX]
                    merged.append(COMPONENT_HEADER[NOTE_IDX])
            log.append(
                f"line {line_no}: duplicate Key {key_field!r} "
                f"(first seen at line {seen[key_field][0]}); "
                f"merged {merged or 'nothing'} into survivor"
            )
            continue
        seen[key_field] = (line_no, len(out_rows))
        out_rows.append(row)

    # Cross-refs: when a Component has multiple Keys (different readings),
    # fill CrossRefs column with the OTHER readings + their member chars.
    # CrossRefs lives at column 10 in the 15-col schema.
    by_component: dict[str, list[int]] = {}
    for idx, row in enumerate(out_rows):
        by_component.setdefault(row[1], []).append(idx)
    for component, indices in by_component.items():
        if len(indices) < 2:
            continue
        for i in indices:
            siblings = [out_rows[j] for j in indices if j != i]
            chunks = [
                f"{sib[2]} / {sib[4]}" if sib[4] else sib[2]
                for sib in siblings
            ]
            out_rows[i][10] = " · ".join(chunks)

    write_output(out_rows, args.out)

    for line in log:
        print(line, file=sys.stderr)
    print(
        f"\nwrote {args.out.name}: {len(out_rows)} rows "
        f"(from {len(src_rows)} source rows, {len(log)} log entries)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
