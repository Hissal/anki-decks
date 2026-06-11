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

# In-repo copy of the source notes (the original lived on the Desktop and kept
# getting deleted). Committed so the full importer stays runnable.
DEFAULT_SOURCE = REPO_ROOT / "scripts" / "sources" / "Selected Notes.txt"

# Components HanziCraft has no dictionary entry for — manual glosses keyed by
# the simplified component character. Applied only when the row's Meaning is
# otherwise blank.
MEANING_OVERRIDES: dict[str, str] = {
    "㐬": "to flow (archaic form, phonetic in 流 / 琉 / 硫)",
    "彡": "hair / decorative strokes (radical)",
    "㢆": "(phonetic component, rare standalone)",
    "尞": "torch / ancient sacrificial fire",
    "畺": "boundary (old form of 疆)",
    "咅": "to spit out (rare; phonetic in 培 / 陪 / 赔)",
    "昷": "warm (old form of 温)",
}

# Curated extra notes keyed by simplified component character. Appended to the
# row's Note (after mechanical cleanup) with a `<br>` separator. Same component
# can appear in multiple rows (different readings) — every row of that component
# gets the note. Empty string = no curated note for this component.
NOTE_OVERRIDES: dict[str, str] = {
    # --- Visual look-alikes ---
    "己": "Visually similar to 已 (yǐ, already) and 巳 (sì, sixth earthly branch). 己 closed on the left, 已 partially closed, 巳 fully closed.",
    "巳": "Visually similar to 己 (jǐ, self) and 已 (yǐ, already). 巳 is fully closed at the top.",
    "甲": "Visually similar to 由 (yóu) and 申 (shēn). 甲 has the vertical stroke going down only; 由 going up only; 申 going through both.",
    "由": "Visually similar to 甲 (jiǎ) and 申 (shēn). 由 has the vertical going up out of the box only.",
    "申": "Visually similar to 甲 (jiǎ) and 由 (yóu). 申 has the vertical going through both top and bottom.",
    "末": "Visually similar to 未 (wèi, not yet). 末 has the LONGER stroke on top (end), 未 has the longer stroke in the middle.",
    "朱": "Visually similar to 末 (mò) and 未 (wèi). 朱 has the extra 丿 stroke through the top.",
    "千": "Visually similar to 干 (gān, dry) and 壬 (rén). 千 has the 丿 stroke on top; 干 is a horizontal line.",
    "卯": "Visually similar to 卬 and 印. 卯 has both halves symmetric.",
    "刃": "刃 = 刀 + a dot marking the blade's edge. Don't confuse with 力 (lì, strength).",
    "夫": "Visually similar to 天 (tiān, sky) and 失 (shī, lose). 夫 has the top horizontal sticking out left.",
    "户": "Visually similar to 尸 (shī, corpse). 户 has an extra dot on top.",
    "厂": "Not in this deck, but ⼚ (cliff radical) looks similar to 广 (yǎn, dotted-cliff).",
    "戊": "Not directly here as a row, but the 戊/戌/戍/戎 family is a notorious confusion cluster.",

    # --- Multi-reading components: which reading is most productive ---
    "肖": "Three readings (xiāo / qiào / shāo) split fairly evenly across compounds — no single dominant set.",
    "青": "Three readings (qīng / jīng / jìng). The jīng/jìng compounds often carry 'essence' or 'still' meanings (精, 静).",
    "工": "Two readings (gōng / gǒng). The gǒng compounds (巩 etc.) are rarer — most 工-compounds take gōng.",
    "比": "Two readings (bǐ / bì). The bǐ set is small (吡妣秕); bì is the more productive direction.",

    # --- Phonetic-set quirks worth flagging ---
    "羊": "Used as a radical (sheep/livestock theme) in many chars where it's NOT the phonetic — e.g. 美, 善, 群. Watch for both roles.",
    "衣": "As a radical the form is 衤 (left) or 衣 split (top/bottom). The phonetic role is much rarer than the semantic one.",
    "心": "Almost always a semantic radical (heart/emotion), not a phonetic. When you see 忄 on the left it's semantic.",
    "口": "Overwhelmingly semantic (speech / opening) rather than phonetic.",
    "贝": "Semantic radical (shells / money / trade) far more often than phonetic.",
    "金": "Semantic (metal) when on the left as 钅. Rare as phonetic.",
    "夂": "Top-down stroke component (winter, complete). Look-alike of 攵 (rap-radical) — distinguish by stroke count.",
    "门": "Frames many chars semantically (gates, doors) but is the phonetic in only a handful (e.g. 们).",

    # --- Etymology hooks that help memory ---
    "禾": "Grain stalk — semantic in 秋, 秒, 秤 etc. (all grain/season/scale themes).",
    "雨": "Weather radical at the top — semantic in 雪, 雷, 霜.",
    "火": "Fire radical; takes the form 灬 at the bottom. Semantic far more than phonetic.",
}
DEFAULT_ENRICH = REPO_ROOT / "scripts" / "cache" / "hanzicraft.json"
DEFAULT_CWC = REPO_ROOT / "scripts" / "cache" / "component_cwc.json"
DEFAULT_CHAR_DATA = REPO_ROOT / "scripts" / "cache" / "char_data.json"
DEFAULT_CHAR_DECOMP = REPO_ROOT / "scripts" / "cache" / "char_decomp.json"
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
# Authoritative member-set helpers — added in the correctness/simplify pass.
#   * pypinyin heteronyms  -> multi-reading sound (fixes single-reading char_data
#     that mis-bucketed polyphonic chars: 蔓 has màn, 轲 has kě, 盛 has chéng…)
#   * opencc t2s           -> simplified-only deck (drops traditional duplicates)
#   * cwc + decomposition  -> containment truth (a member must actually CONTAIN
#     the component; this is what 于's bogus 余餘予馀 violated)
# ---------------------------------------------------------------------------

from pypinyin import pinyin as _pinyin, Style as _Style  # noqa: E402
from opencc import OpenCC as _OpenCC  # noqa: E402

_T2S = _OpenCC("t2s")


def to_simplified(ch: str) -> str:
    """opencc traditional→simplified for a single char (no-op if already simp)."""
    return _T2S.convert(ch)


def _norm_syllable(s: str) -> str:
    return s.strip().lower().replace("ü", "v").replace("u:", "v")


def char_readings(ch: str) -> list[tuple[str, int]]:
    """All (syllable, tone) readings for a char via pypinyin heteronyms.
    Tone 5 = neutral. Returns [] when pypinyin has no Han reading."""
    try:
        raw = _pinyin(ch, style=_Style.TONE3, heteronym=True)
    except Exception:
        return []
    out: list[tuple[str, int]] = []
    for r in (raw[0] if raw else []):
        if not r:
            continue
        tone = int(r[-1]) if r[-1].isdigit() else 5
        syl = _norm_syllable(r[:-1] if r[-1].isdigit() else r)
        if syl:
            out.append((syl, tone))
    return out


def component_contains(component: str, ch: str,
                       cwc: dict | None,
                       char_decomp: dict | None) -> tuple[bool, bool]:
    """Does `ch` contain `component`? Returns (contained, have_evidence).

    Truth order: ch == component, then cwc[component] membership (HanziCraft),
    then the component appearing anywhere in ch's decomposition tree
    (char_decomp once+radical, recursed). have_evidence=False only when there is
    no decomp data at all -> caller treats containment as UNKNOWN, not False."""
    if ch == component:
        return True, True
    if cwc and ch in set(cwc.get(component, [])):
        return True, True
    if not char_decomp:
        return False, False
    seen: set[str] = set()

    def rec(c: str, depth: int) -> bool:
        if depth < 0 or c in seen:
            return False
        seen.add(c)
        d = char_decomp.get(c)
        if not d:
            return False
        for key in ("once", "radical"):
            for p in (d.get(key) or []):
                if not p or p == UNGLYPHABLE:
                    continue
                if p == component or rec(p, depth - 1):
                    return True
        return False

    return rec(ch, 5), (ch in char_decomp)


def clean_member_bucket(component: str, raw_members: str, row_pinyin_numeric: str,
                        cwc: dict | None, char_decomp: dict | None,
                        log: list[str], line_no: int):
    """Simplify + containment-filter + tone-classify a curated MemberChars set.

    Returns (bucket1_exact_tone, moved_same_syllable, dropped). Members that do
    not contain the component, or whose sound shares neither syllable nor tone,
    are dropped. Same-syllable / different-tone members are split off to bucket 2.
    """
    exp_syl = _norm_syllable(strip_tone(row_pinyin_numeric))
    exp_tone = (int(row_pinyin_numeric[-1])
                if row_pinyin_numeric and row_pinyin_numeric[-1].isdigit() else 5)
    exp = (exp_syl, exp_tone)
    seen: set[str] = set()
    bucket1: list[str] = []
    moved: list[str] = []
    dropped: list[str] = []
    for ch in raw_members:
        s = to_simplified(ch)
        if not s or s == component or s in seen:
            continue
        seen.add(s)
        contained, have = component_contains(component, s, cwc, char_decomp)
        if not contained:
            # STRICT: a member must positively contain the component GLYPH (cwc
            # raw membership or decomposition). This drops chars where
            # simplification replaced the component (杨 has 𠃓 not 昜; 卫 not 韦)
            # and unverifiable rares — exactly the "teaches a glyph you'll never
            # see" mistakes we must not ship.
            dropped.append(f"{ch}->{s}(no-contain,have={have})")
            continue
        rds = char_readings(s)
        if not rds:
            bucket1.append(s)  # contained; pypinyin just lacks a reading (rare)
            continue
        syls = {sy for sy, _ in rds}
        if exp in rds:
            bucket1.append(s)
        elif exp_syl in syls:
            moved.append(s)
        else:
            dropped.append(f"{ch}->{s}(diff-syllable,{rds})")
    if dropped or moved:
        log.append(
            f"line {line_no}: {component} MemberChars cleaned — "
            f"kept={''.join(bucket1)} moved→bucket2={''.join(moved)} dropped={dropped}"
        )
    return bucket1, moved, dropped


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
# Junk to drop: bare CJK chars, X/Y stats with or without qualifiers, ASCII strays.
CJK_ONLY_RE = re.compile(r"^[㐀-鿿]+$")
STAT_FRAG_RE = re.compile(r"^\s*\d+\s*/\s*\d+(\s+.*)?$")
ALWAYS_PATTERN_RE = re.compile(r"^\s*al+ways\s+(.+?)\s*$", re.IGNORECASE)


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


_LABEL_PREFIXES = (
    "Traditional:",
    "Variant:",
    "See also:",
    "Note similarity",
    "thousand.",  # multiline continuation of `Note similarity to 万…`
    "corpse.",    # continuation of 户's similarity blurb
)


def reformat_note_hints(note: str) -> str:
    """Walk a `<br>`-joined Note. Keep labeled hints + reformat `-X` / `+X` /
    `always …` patterns. Drop everything else (bare CJK chars, X/Y stats,
    ASCII strays) — that data lives in Decomposition / the A/B/C triple."""
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
        m = ALWAYS_PATTERN_RE.match(t)
        if m:
            out.append(f"Sound pattern: always {m.group(1)}")
            continue
        if t.startswith(_LABEL_PREFIXES):
            out.append(t)
            continue
        # Drop: bare CJK chars (info in Decomposition), X/Y stats (info in
        # A/B/C triple), and any remaining ASCII scratch tokens.
        if CJK_ONLY_RE.match(t):
            continue
        if STAT_FRAG_RE.match(t):
            continue
        # Catch-all: drop. Was reached for `dan4`, `jailer`, `u2 - another 8/27` etc.
        # Anything we want to keep should match one of the rules above.
    return "<br>".join(out)


UNGLYPHABLE = "No glyph available"


def _clean_decomp_parts(parts: list[str]) -> list[str]:
    """Replace HanziCraft's `No glyph available` placeholder with `?`."""
    return ["?" if p == UNGLYPHABLE else p for p in parts]


def _emit_decomp_segment(kind: str, parts: list[str], component: str) -> str | None:
    """Format one segment (`once:…` or `radical:…`). Returns None when the
    segment should be skipped (atomic / unusable / equal to the component)."""
    if not parts:
        return None
    # All-? placeholder → no real data
    if all(p == "?" for p in parts):
        return None
    # Single piece equal to the component → trivially redundant
    if len(parts) == 1 and parts[0] == component:
        return None
    # Single distinct piece — HanziCraft's stub for doubled/tripled forms
    # (e.g. 比 = 匕+匕 stored as just ["匕"]). Render as "X × 2" so the card
    # doesn't look incomplete.
    if len(parts) == 1:
        return f"{kind}:{parts[0]}×2"
    return f"{kind}:" + "+".join(parts)


def build_decomposition(component: str, hc_decomp: dict | None) -> str:
    """Pack the component's own top-level decomposition into a tiny TSV-safe
    string: `once:一+丄;radical:工`. Skips parts that are trivially equal
    to the component itself, or are all-`?` placeholders."""
    if not hc_decomp:
        return ""
    parts: list[str] = []
    once_seg = _emit_decomp_segment(
        "once", _clean_decomp_parts(hc_decomp.get("once") or []), component
    )
    if once_seg:
        parts.append(once_seg)
    rad_seg = _emit_decomp_segment(
        "radical", _clean_decomp_parts(hc_decomp.get("radical") or []), component
    )
    if rad_seg:
        parts.append(rad_seg)
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
    moved: list[str],
    cwc: dict[str, list[str]] | None,
    char_decomp: dict[str, dict] | None,
) -> str:
    """Bucket 2 = chars that CONTAIN the component and share this row's syllable
    but differ in tone. Built from: (a) members moved out of bucket 1 for tone,
    then (b) a walk of cwc[component], simplified (opencc) and read via pypinyin
    heteronyms. A char with an exact-tone reading is excluded (it qualifies for
    bucket 1, not 2). Output is simplified + de-duplicated."""
    target_syllable = _norm_syllable(strip_tone(row_pinyin_numeric))
    target_tone = (int(row_pinyin_numeric[-1])
                   if row_pinyin_numeric and row_pinyin_numeric[-1].isdigit() else 5)
    if not target_syllable:
        return ""
    in_bucket1 = set(member_chars)
    result: list[str] = []
    seen: set[str] = set()

    def _add(s: str) -> None:
        if s and s != component and s not in in_bucket1 and s not in seen:
            seen.add(s)
            result.append(s)

    # (a) chars demoted from bucket 1 (already simplified + contained + same-syllable)
    for ch in moved:
        _add(ch)

    # (b) the full characters-with-this-component list
    for ch in (cwc.get(component) if cwc else None) or []:
        s = to_simplified(ch)
        if s == component or s in in_bucket1 or s in seen:
            continue
        # Glyph-level containment: the simplified form must still contain the
        # component (drops 衛→卫 under 韦, where simplification removed it).
        contained, _ = component_contains(component, s, cwc, char_decomp)
        if not contained:
            continue
        rds = char_readings(s)
        if not rds:
            continue
        syls = {sy for sy, _ in rds}
        if target_syllable in syls and (target_syllable, target_tone) not in rds:
            _add(s)
    return "".join(result)


def _decomp_usable(parts: list[str] | None, ch: str) -> bool:
    """A decomp is usable when it has parts, none unglyphable, and isn't just
    the char repeating itself."""
    if not parts:
        return False
    if any(p == "?" for p in parts):
        return False
    if len(parts) == 1 and parts[0] == ch:
        return False
    return True


def build_member_decomp(
    component: str,
    bucket1: str,
    bucket2: str,
    char_decomp: dict[str, dict] | None,
    enrich: dict[str, dict] | None,
) -> str:
    """Pack `巩=工+凡|汞=工+水`-style per-char decomp for Card 2 back.

    Prefers HanziCraft's top-level `once` split — the clean phonetic+rest
    breakdown (河 → 氵 + 可). But `once` sometimes hides the component one
    level down (the same nesting problem the radicals deck has). When `once`
    fails to surface the component, fall back to the full `radical`
    decomposition, which atomizes to base components and does contain it — the
    point of Card 2 is to highlight the shared phonetic in every member."""
    if not (char_decomp or enrich):
        return ""
    needle = {component}
    pieces: list[str] = []
    seen: set[str] = set()

    def _surfaces(parts: list[str]) -> bool:
        return any(p in needle for p in parts)

    for ch in list(bucket1) + list(bucket2):
        if ch in seen:
            continue
        seen.add(ch)

        d = (char_decomp or {}).get(ch) if char_decomp else None
        once = (d.get("once") if d else None) or None
        rad = (d.get("radical") if d else None) or None
        if (once is None or rad is None) and enrich and enrich.get(ch):
            edec = enrich[ch].get("decomposition") or {}
            once = once or (edec.get("once") or None)
            rad = rad or (edec.get("radical") or None)

        once_c = _clean_decomp_parts(once) if once else None
        rad_c = _clean_decomp_parts(rad) if rad else None

        # Priority: clean `once` that surfaces the component → full `radical`
        # decomp that surfaces it → any usable `once` → any usable `radical`.
        if _decomp_usable(once_c, ch) and _surfaces(once_c):
            chosen = once_c
        elif _decomp_usable(rad_c, ch) and _surfaces(rad_c):
            chosen = rad_c
        elif _decomp_usable(once_c, ch):
            chosen = once_c
        elif _decomp_usable(rad_c, ch):
            chosen = rad_c
        else:
            continue

        pieces.append(f"{ch}={'+'.join(chosen)}")
    return "|".join(pieces)


def transform_row(
    fields: list[str],
    line_no: int,
    log: list[str],
    enrich: dict[str, dict] | None,
    cwc: dict[str, list[str]] | None,
    char_data: dict[str, dict] | None,
    char_decomp: dict[str, dict] | None,
    present_components: set[str] | None = None,
) -> list[str] | None:
    """Map a 10-col source row → 16-col output row. Returns None to skip."""
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

    # Full-simplify pass: the deck is simplified-only. If this row's component is
    # a traditional character, either drop it (a simplified twin row exists -> the
    # whole series is redundant) or relabel it to simplified (no twin row, e.g.
    # 馬/見/門 -> 马/见/门, so the series survives in simplified form).
    if to_simplified(component) != component:
        simp = to_simplified(component)
        if present_components and simp in present_components:
            log.append(
                f"line {line_no}: dropped redundant traditional component "
                f"{component!r} (simplified twin {simp!r} already a row)"
            )
            return None
        log.append(
            f"line {line_no}: relabeled trad-only component {component!r} -> {simp!r}"
        )
        component = simp

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

    raw_members = strip_component_from_set(component, src_set)
    member_chars_list, moved_to_bucket2, _dropped = clean_member_bucket(
        component, raw_members, src_pinyin, cwc, char_decomp, log, line_no
    )
    member_chars = "".join(member_chars_list)

    # No valid exact-tone member survived containment+tone filtering. The
    # component is either bogus (皀: HanziCraft lists no real series) or an
    # archaic phonetic shape that simplification replaced (昜→𠃓, 巠, 睪…), so it
    # can't be taught as a simplified glyph. Drop the row (logged — these are the
    # candidates for the later "same-syllable-only" phase).
    if not member_chars:
        log.append(
            f"line {line_no}: DROPPED row {component!r}:{src_pinyin} — no valid "
            f"exact-tone member after containment+tone filtering "
            f"(raw members were {raw_members!r})"
        )
        return None

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
    elif component in MEANING_OVERRIDES:
        # Fall back to a manual gloss for obscure components HanziCraft has no
        # dictionary entry for (phase 3D-4).
        meaning_value = MEANING_OVERRIDES[component]
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
    # Phase 3D-2 Part B: append curated note when one exists for this component.
    curated = NOTE_OVERRIDES.get(component, "").strip()
    if curated:
        note = (note + "<br>" + curated) if note else curated

    decomposition = build_decomposition(component, hc_decomp)

    same_syllable_chars = compute_same_syllable_bucket(
        component=component,
        row_pinyin_numeric=src_pinyin,
        member_chars=member_chars,
        moved=moved_to_bucket2,
        cwc=cwc,
        char_decomp=char_decomp,
    )

    member_decomp = build_member_decomp(
        component=component,
        bucket1=member_chars,
        bucket2=same_syllable_chars,
        char_decomp=char_decomp,
        enrich=enrich,
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
        hc_productivity_str,
        hc_freq_rank,
        decomposition,
        member_decomp,
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
    ap.add_argument("--char-decomp", type=Path, default=DEFAULT_CHAR_DECOMP,
                    help="per-character once-level decomp cache (optional)")
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

    char_decomp: dict[str, dict] | None = None
    if args.char_decomp.exists():
        try:
            char_decomp = json.loads(args.char_decomp.read_text(encoding="utf-8"))
            print(f"loaded char decomp for {len(char_decomp)} chars from {args.char_decomp}",
                  file=sys.stderr)
        except Exception as e:
            print(f"warn: failed to load char-decomp file {args.char_decomp}: {e}",
                  file=sys.stderr)

    log: list[str] = []
    src_rows = read_source(args.source, log)

    out_rows: list[list[str]] = []
    seen: dict[str, tuple[int, int]] = {}  # key_field -> (src_line, out_index)
    # Field indices for the 15-col schema (Reliability dropped in 3D-1):
    #  0=Key, 1=Component, 2=Pinyin, 3=Meaning, 4=MemberChars,
    #  5=SameSyllableChars, 6=Productivity, 7=Frequency,
    #  8=Decomposition, 9=MemberDecomp, 10=CrossRefs, 11=Note,
    #  12=Link, 13=Audio, 14=Tags
    MERGE_COPY_IF_EMPTY = (3, 4, 5, 6, 7, 8, 9, 12, 13)
    NOTE_IDX = 11

    # Components that already exist as their own (simplified) row. Used to decide
    # whether a traditional-component row is a redundant duplicate (drop) or the
    # only carrier of its series (relabel to simplified).
    present_components: set[str] = set()
    for _ln, _f in src_rows:
        if len(_f) > 1:
            c = strip_html_noise(_f[1])
            if c and has_cjk(c) and to_simplified(c) == c:
                present_components.add(c)

    for line_no, fields in src_rows:
        try:
            row = transform_row(fields, line_no, log, enrich, cwc, char_data,
                                char_decomp, present_components)
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

    # Sort rows for learning-order: phonetic leverage descending.
    # Score = A * 100 + B * 10 + Productivity, with A = len(MemberChars) and
    # B = A + len(SameSyllableChars). High exact-phonetic-match components rank
    # first; pure semantic radicals (high productivity but low A) drop down.
    # Frequency rank ascends as a tiebreak (more common chars first).
    INF = 10**9
    def _sort_key(row: list[str]) -> tuple:
        a = len(row[4])
        b = a + len(row[5])
        try:
            prod = int(row[6]) if row[6] else 0
        except ValueError:
            prod = 0
        try:
            freq = int(row[7]) if row[7] else INF
        except ValueError:
            freq = INF
        return (-(a * 100 + b * 10 + prod), freq, row[1], row[2])
    out_rows.sort(key=_sort_key)

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
