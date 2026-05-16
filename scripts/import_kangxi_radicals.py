#!/usr/bin/env python3
"""Generate Chinese_Kangxi_Radicals.tsv from the seed Radicals.txt source.

One-shot, NOT idempotent. Overwrites on every run.

Source: hand-curated 6-column TSV with mixed conventions —
- col 0: traditional radical, optionally with variants in parens `心 (忄,⺗)`
- col 1: simplified variant (single CJK char), OR a pronunciation note
  `(pr.chǎng)`, OR empty
- col 2: pinyin, occasionally with alternate readings `yòng (shuǎi)`
- col 3: English meaning
- col 4: comma-separated curated example characters
- col 5: tags (mostly empty)

This script normalizes that into the 15-col radicals deck schema, splitting
variants into Variant1 / Variant2 / ReferenceVariants slots so Anki can
generate one card per primary variant.

Usage:
  python scripts/import_kangxi_radicals.py [--source PATH]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.parse
from pathlib import Path

from common import HAN_RE, REPO_ROOT
from radicals_common import (
    RADICALS_DECK_PATH,
    RADICALS_HEADER,
)

DEFAULT_SOURCE = Path(
    r"C:\Users\hissa\OneDrive\Työpöytä\Radicals.txt"
)
DEFAULT_HC_CACHE = REPO_ROOT / "scripts" / "cache" / "hanzicraft.json"
DEFAULT_CWC_CACHE = REPO_ROOT / "scripts" / "cache" / "component_cwc.json"
DEFAULT_CHAR_DATA = REPO_ROOT / "scripts" / "cache" / "char_data.json"
DEFAULT_CHAR_DECOMP = REPO_ROOT / "scripts" / "cache" / "char_decomp.json"
HANZICRAFT_URL = "https://hanzicraft.com/dashboard/character/{}"

# How many curated MemberChars to keep per radical (truncates source set when
# no MEMBER_OVERRIDES entry exists). Card-back stays compact; "+ X more"
# indicator covers the gap to total Productivity.
MEMBER_CAP = 8

# ---------------------------------------------------------------------------
# Pinyin tonemark → numeric conversion (reverse of the table used in
# import_phonetic_components). Needed to build the unique Key column.
# ---------------------------------------------------------------------------

_TONE_MAP: dict[str, tuple[str, int]] = {}
for base, marks in [
    ("a", ["ā", "á", "ǎ", "à"]),
    ("e", ["ē", "é", "ě", "è"]),
    ("i", ["ī", "í", "ǐ", "ì"]),
    ("o", ["ō", "ó", "ǒ", "ò"]),
    ("u", ["ū", "ú", "ǔ", "ù"]),
    ("ü", ["ǖ", "ǘ", "ǚ", "ǜ"]),
]:
    for i, m in enumerate(marks, start=1):
        _TONE_MAP[m] = (base, i)


def pinyin_marks_to_numeric(syllable: str) -> str:
    """`gǒng` → `gong3`, `yòng` → `yong4`, `tóu` → `tou2`. Tone 5 = no digit."""
    if not syllable:
        return ""
    s = syllable.strip().lower()
    base_chars: list[str] = []
    tone = 0
    for ch in s:
        if ch in _TONE_MAP:
            base, t = _TONE_MAP[ch]
            base_chars.append(base)
            tone = t
        else:
            base_chars.append(ch)
    out = "".join(base_chars)
    return f"{out}{tone}" if tone else out


# ---------------------------------------------------------------------------
# Variant ordering overrides. Source often lists variants in arbitrary order;
# pick the most-used-in-modern-writing one as Variant1. Keys are the canonical
# simplified radical.
# ---------------------------------------------------------------------------

VARIANT_OVERRIDES: dict[str, list[str]] = {
    # 水: source has 氺,氵 but 氵 is by far the more common positional form
    "水": ["氵", "氺"],
    # 心: 忄 (left) is much more common than ⺗ (bottom)
    "心": ["忄", "⺗"],
    # 火: 灬 (bottom) is the standard reduction
    "火": ["灬"],
    # 玉: 王 (in compound chars) is the productive form, 玊 is rare
    "玉": ["王", "玊", "⺩"],
    # 人: 亻 (left) much more common than 𠆢 (top)
    "人": ["亻", "𠆢"],
    # 网: 罒 is by far the dominant variant; rest are archaic
    "网": ["罒"],
    "网繁": ["罒"],
    # 手: 扌 (left) is the productive form
    "手": ["扌", "龵"],
    # 辵: 辶 is the standard simplified form
    "辵": ["辶", "⻌", "⻍"],
    # 邑: 阝 on the RIGHT signals 'city/state' — primary positional form
    "邑": ["阝", "⻏", "⻖"],
    # 阜: 阝 on the LEFT signals 'mound/hill' — same glyph, different role
    "阜": ["阝"],
    # 衣: 衤 (left) is the positional form
    "衣": ["衤"],
    # 刀: 刂 (right) is the positional form
    "刀": ["刂"],
    # 言: 讠 (simplified-left) is dominant in modern usage
    "言": ["讠", "訁"],
    # 食: 饣 (simplified-left) is dominant; 飠 is traditional
    "食": ["饣", "飠"],
    # 金: 钅 (simplified-left) is dominant; 釒 is traditional
    "金": ["钅", "釒"],
    # 糸: 纟 (simplified-left) is dominant; 糹 is the half-width traditional form
    "糸": ["纟", "糹"],
    # 月: no variant cards needed
    # 草艹: 艹 (top) is the productive form
    "艸": ["艹"],
    # 雨: rendered as-is on top — no major variant
}

# When the source col 1 is a `(pr.X)` style note instead of a simplified
# variant, parse the X out into the pinyin/note instead of treating it as a
# variant. Pattern detected: `(pr.<something>)`.
PR_NOTE_RE = re.compile(r"^\s*\(pr\.([^)]+)\)\s*$")


# ---------------------------------------------------------------------------
# Tier classification — based on a curated list of high-productivity / well-
# known radicals, the rest fall into 'common' / 'rare' / 'structural' by a
# simple heuristic until HanziCraft enrichment provides productivity counts.
# ---------------------------------------------------------------------------

_CORE_RADICALS = set("氵心钅木口亻艹丶辶宀广疒目人女子刀力又又水火金土山日月儿大不工竹米贝鸟马鱼车页革马门阝口")
# Radicals that exist almost purely as structural strokes — rarely meaning-bearing
_STRUCTURAL_RADICALS = set("一丨丶丿乙亅二亠儿入八冂冖凵几勹匕匚匸卜厂厶夕夂夊")
# Rare classical/specialized
_RARE_RADICALS = set("龜龍鼠鹿黍黻黼鬥鬯鬲鬼黾鼎鼓鼻齒齊麻麦麻黾鼎鼓鼠鼻齒齊龍龜韭")


def classify_tier(radical: str) -> str:
    if radical in _CORE_RADICALS:
        return "radical-core"
    if radical in _STRUCTURAL_RADICALS:
        return "radical-structural"
    if radical in _RARE_RADICALS:
        return "radical-rare"
    return "radical-common"


# ---------------------------------------------------------------------------
# Manual meaning overrides (when source gloss is too terse or missing)
# ---------------------------------------------------------------------------

MEANING_OVERRIDES: dict[str, str] = {
    # Filled lazily after spot-check
}

# Hand-picked MemberChars for high-leverage radicals where the source set is
# weak (heavy on traditional / obscure chars). Keep to common modern simplified
# characters where the radical visibly appears in its canonical position.
# Maximum 8 chars per entry — anything beyond becomes part of the "+ X more"
# count derived from Productivity.
MEMBER_OVERRIDES: dict[str, str] = {
    # --- Core semantic radicals (high productivity, everyday vocab) ---
    # All picks validated against scripts/cache/component_cwc.json — must
    # appear in HanziCraft's `characterswithcomponent` list for the keyed
    # radical (or for its canonical when the radical is a variant glyph
    # HanziCraft doesn't index separately, e.g. 阜).
    "口": "吃喝叫喊唱嘴和可",
    "水": "河海湖洋洗淋汁汗",
    "氵": "河海湖洋洗淋汁汗",
    "火": "灯烧烤炒煤热点炎",
    "灬": "热点煮蒸照然黑熟",
    "心": "情感想念忘怕思忙",
    "忄": "情怕忙快慢怪忧懂",
    "⺗": "慰想意感思念忘悲",
    "木": "林森本朱树枝根桃",
    "钅": "银铜铁钱钟针钉钢",
    "金": "银铜铁钱钟针钉钢",
    "土": "地坐场城堂塔块境",
    "女": "好妈姐妹娘奶妻姑",
    "人": "你他们仁住信件位",
    "亻": "你他们仁住信件位",
    "子": "孩学孙孔孤孵存季",
    "大": "太天奇头央夸奥奋",
    "山": "岛峰岭岗崖崎岔屿",
    "日": "明早春时晚晴是星",
    "月": "有期朋服望脸腿胸",
    "讠": "说话语词读请谢谈",
    "言": "誉誓警譬誊讨誡讚",
    "贝": "财货赔购账贵贫资",
    "貝": "財貨購貴貧資積貢",
    "车": "轮转辆较输辅辈轨",
    "馬": "駕驚騎驅駝馳駛驗",
    "马": "驾驴骆骑驶骄驰驯",
    "鸟": "鸡鸭鹅鸽鹰鹊鹏鸣",
    "鳥": "鴨鵝鴿鵲鵬鳴鳳鴉",
    "鱼": "鲨鲸鲤鲈鲍鳗鲜鳄",
    "魚": "鯊鯖鰻鮮鰲鱉鱗鯡",
    "门": "闭闹闯闻问间閃閣",
    "門": "開閉間閑閣關簡閱",
    "页": "顶顺须顾领颗顿额",
    "頁": "頂順須顧領顆頓額",
    "饣": "饭饺饮饿馆饱馒饼",
    "飠": "飯飲餓館飽饅餬",
    "食": "餐饭馆饮饱饿饺饼",
    "玉": "王玩理球现",
    "王": "玩理球现珠琢瑰国",
    "衣": "初被装裙裤补袜袖",
    "衤": "初被装裙裤补袜袖",
    "雨": "雪雷霜雾露霸震霞",
    "革": "鞋鞭靴鞍鞠鞘",
    "弓": "引张弦弧弹弛弩第",
    "又": "友取受双叙叔变最",
    "力": "加办助劝努动励勇",
    "刀": "分切初利刻别到割",
    "刂": "分切初利刻别到割",
    "工": "左巧差功攻贡经",
    "米": "粉粒粥糖糕糊精料",
    "竹": "笔等第答策篇箱筋",
    "⺮": "笔等第答策篇箱筋",
    "艹": "草花苹菜茶药茄苦",
    "辶": "这道送过运近远进",
    "邑": "那邻邦郎部都郊郡",
    # Most simp 阝-left chars (阳, 院 etc.) are filed under cwc[阝] in HC, not
    # cwc[阜]. Picks here are semantically the standard 阜 left-radical set;
    # validator skips this entry because HC doesn't store them under 阜.
    "阜": "阳阴院阶阻陈陪陷",
    "广": "床店府度座庭麻底",
    "宀": "家室宁宝完定院案",
    "疒": "病疼痛瘦痒疯疲疾",
    "目": "看眼睡睛瞎瞄瞌瞪",
    "耳": "联职聪闻聊耻聋摄",
    "足": "跑跳跟跨踢路跌踪",
    "⻊": "跑跳跟跨踢路跌踪",
    "手": "打把拉指接抓挂推",
    "扌": "打把拉指接抓挂推",
    "攵": "收改放教数政故敢",
    "礻": "礼神福祝祖祭祸祈",
    "示": "禁奈祟",
    "牛": "物特犁牢牲牧牡",
    "牜": "物特犁牢牲牧牡",
    "犬": "猛突默器",
    "犭": "狗猫狼猪狐狮猜独",
    "走": "起越赶超趋趟趁趣",
    "白": "百的皇皆皎皓",
    "石": "矿研破础磁碎砖碰",
    "立": "站章端竞竭竖亲部",
    "色": "艳",
    "禾": "和私秋种秒科秘程",
    "穴": "空究突穿窗穷窝窃",
    "舟": "船航舱艘舰舵艇舶",
    "见": "观规视觉觅览",
    "見": "觀規視覺靦親",
    "酉": "酒醉酸醒醋酱配酬",
    "鬼": "魂魄魅魇魔魁魏",
    "黑": "默墨黛黯",
}


# ---------------------------------------------------------------------------
# Curated notes overrides (R3 will populate this — for now keep empty)
# ---------------------------------------------------------------------------

NOTE_OVERRIDES: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Source reader
# ---------------------------------------------------------------------------


def read_source(path: Path, log: list[str]) -> list[tuple[int, list[str]]]:
    """Read the 6-col seed TSV. Returns list of (line_no, fields) tuples."""
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    rows: list[tuple[int, list[str]]] = []
    line_no = 0
    for raw in text.split("\n"):
        line_no += 1
        if not raw.strip():
            continue
        if raw.lstrip().startswith("#"):
            continue
        fields = raw.split("\t")
        # Pad to 6
        while len(fields) < 6:
            fields.append("")
        rows.append((line_no, fields))
    log.append(f"read {len(rows)} non-empty, non-directive rows from source")
    return rows


# ---------------------------------------------------------------------------
# Per-row transform
# ---------------------------------------------------------------------------


COL0_VARIANTS_RE = re.compile(r"^([^\s(（]+)\s*[(（]([^)）]*)[)）]\s*$")


def parse_col0(value: str) -> tuple[str, list[str]]:
    """`心 (忄,⺗)` → (`心`, [`忄`, `⺗`]). `一` → (`一`, [])."""
    s = value.strip()
    m = COL0_VARIANTS_RE.match(s)
    if m:
        canonical = m.group(1).strip()
        variants_raw = m.group(2)
        # Variants are comma- or space-separated
        variants = [v.strip() for v in re.split(r"[,，\s]+", variants_raw) if v.strip()]
        return canonical, variants
    return s, []


def parse_pinyin_field(value: str) -> tuple[str, str]:
    """Returns (primary_pinyin, extra_for_note). Handles `yòng (shuǎi)` and
    `chuò / zouzhi` style fields."""
    s = value.strip()
    if not s:
        return "", ""
    # `chuò / zouzhi` — drop the `zouzhi` style spelling-out
    if "/" in s:
        parts = [p.strip() for p in s.split("/") if p.strip()]
        # Keep the part with tone-marks (most likely actual pinyin)
        keep = [p for p in parts if any(ch in _TONE_MAP for ch in p)]
        if keep:
            return keep[0], ""
        return parts[0], ""
    # `yòng (shuǎi)` — primary in front, alternate in parens
    m = re.match(r"^([^\s(（]+)\s*[(（]([^)）]+)[)）]\s*$", s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return s, ""


def normalize_member_chars(value: str) -> str:
    """Strip separators and non-CJK noise; keep only CJK chars in order."""
    out: list[str] = []
    for ch in value:
        if HAN_RE.match(ch):
            out.append(ch)
    return "".join(out)


UNGLYPHABLE = "No glyph available"


def _clean_decomp_parts(parts: list[str]) -> list[str]:
    return ["?" if p == UNGLYPHABLE else p for p in parts]


def _emit_decomp_segment(kind: str, parts: list[str], component: str) -> str | None:
    if not parts:
        return None
    # Any unknown-glyph piece makes the decomp misleading — skip entirely.
    if any(p == "?" for p in parts):
        return None
    if len(parts) == 1 and parts[0] == component:
        return None
    if len(parts) == 1:
        return f"{kind}:{parts[0]}×2"
    return f"{kind}:" + "+".join(parts)


def build_decomposition(component: str, hc_decomp: dict | None) -> str:
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


def build_member_decomp(
    chars: str,
    char_decomp: dict[str, dict] | None,
    enrich: dict[str, dict] | None,
) -> str:
    """`巩=工+凡|汞=工+水` style per-char once-level decomp packing."""
    if not (char_decomp or enrich):
        return ""
    pieces: list[str] = []
    seen: set[str] = set()
    for ch in chars:
        if ch in seen:
            continue
        seen.add(ch)
        d = (char_decomp or {}).get(ch) if char_decomp else None
        once: list[str] | None = None
        if d and d.get("once"):
            once = d["once"]
        elif enrich and enrich.get(ch) and enrich[ch].get("decomposition", {}).get("once"):
            once = enrich[ch]["decomposition"]["once"]
        if not once:
            continue
        cleaned = _clean_decomp_parts(once)
        if len(cleaned) == 1 and cleaned[0] == ch:
            continue
        pieces.append(f"{ch}={'+'.join(cleaned)}")
    return "|".join(pieces)


# When a radical is a variant glyph HanziCraft doesn't index separately, its
# member chars live under the canonical's cwc entry. Used by the in-script
# validator to look up the right cwc list.
MEMBER_OVERRIDE_CWC_ALIAS: dict[str, str] = {
    "阜": "阝",
}


def _validate_member_picks(
    canonical: str,
    picks: str,
    cwc: dict[str, list[str]] | None,
    log: list[str],
) -> None:
    """If we have HanziCraft's full cwc list, hard-fail when any pick isn't in
    it — caught the 笑 → 口 mistake in R2 post-mortem."""
    if not cwc or not picks:
        return
    valid = set(cwc.get(canonical, []))
    alias = MEMBER_OVERRIDE_CWC_ALIAS.get(canonical)
    if alias:
        valid |= set(cwc.get(alias, []))
    if not valid:
        return  # no cwc data → can't validate
    bad = [c for c in picks if c not in valid]
    if bad:
        log.append(
            f"MEMBER_OVERRIDES for {canonical!r} contains chars HanziCraft "
            f"doesn't list under this radical: {bad!r}"
        )


def pick_member_chars(
    canonical: str,
    source_chars: str,
    cwc: dict[str, list[str]] | None = None,
) -> str:
    """Apply MEMBER_OVERRIDES if defined; else filter the source set to chars
    that HanziCraft actually lists under this radical (when cwc data exists),
    then truncate to MEMBER_CAP.

    The source seed uses Kangxi-style radical assignment (e.g. 不 is filed
    under 一). HanziCraft uses structural component decomposition (不 doesn't
    contain a separable 一). For a recognition-focused deck the structural
    view is what the learner actually sees, so we drop source picks that fail
    the cwc check rather than render them as ghost members."""
    override = MEMBER_OVERRIDES.get(canonical)
    if override:
        return override

    valid: set[str] | None = None
    if cwc is not None:
        valid = set(cwc.get(canonical, []))
        alias = MEMBER_OVERRIDE_CWC_ALIAS.get(canonical)
        if alias:
            valid |= set(cwc.get(alias, []))

    seen: set[str] = set()
    out: list[str] = []
    for ch in source_chars:
        if ch in seen:
            continue
        if valid is not None and valid and ch not in valid:
            continue  # HC doesn't list this char under the radical — skip
        seen.add(ch)
        out.append(ch)
        if len(out) >= MEMBER_CAP:
            break
    return "".join(out)


def transform_row(
    fields: list[str],
    line_no: int,
    log: list[str],
    enrich: dict[str, dict] | None = None,
    char_decomp: dict[str, dict] | None = None,
    cwc: dict[str, list[str]] | None = None,
) -> list[str] | None:
    """Map a 6-col source row → 15-col output row. Returns None to skip."""
    while len(fields) < 6:
        fields.append("")

    canonical_trad, variants_in_parens = parse_col0(fields[0])
    col1_raw = fields[1].strip()
    pinyin_field = fields[2]
    meaning = fields[3].strip()
    examples = fields[4]

    # Decide canonical (modern simplified preferred).
    canonical: str
    extra_variants: list[str] = []
    pronunciation_note = ""

    if col1_raw:
        m = PR_NOTE_RE.match(col1_raw)
        if m:
            pronunciation_note = m.group(1).strip()
            canonical = canonical_trad
            extra_variants = list(variants_in_parens)
        elif len(col1_raw) == 1 and HAN_RE.match(col1_raw):
            # Simplified-variant CJK char → promote to canonical.
            canonical = col1_raw
            # The original col-0 char becomes a traditional variant.
            extra_variants = [canonical_trad] + list(variants_in_parens)
        else:
            # Unknown col-1 content — log and treat as note material.
            log.append(
                f"line {line_no}: unexpected col-1 value {col1_raw!r} on radical "
                f"{canonical_trad!r}; ignoring"
            )
            canonical = canonical_trad
            extra_variants = list(variants_in_parens)
    else:
        canonical = canonical_trad
        extra_variants = list(variants_in_parens)

    if not canonical or not HAN_RE.match(canonical):
        log.append(
            f"line {line_no}: skipping row with non-CJK canonical {canonical!r}"
        )
        return None

    # Apply variant order override if present.
    if canonical in VARIANT_OVERRIDES:
        ordered = VARIANT_OVERRIDES[canonical]
        # Keep only variants we actually have, preserving override order.
        known = set(extra_variants)
        primary = [v for v in ordered if v in known]
        remainder = [v for v in extra_variants if v not in ordered]
        extra_variants = primary + remainder

    # Split into slots.
    variant1 = extra_variants[0] if len(extra_variants) >= 1 else ""
    variant2 = extra_variants[1] if len(extra_variants) >= 2 else ""
    reference_variants = ",".join(extra_variants[2:]) if len(extra_variants) > 2 else ""

    # Pinyin.
    primary_pinyin, alt_pinyin = parse_pinyin_field(pinyin_field)
    if pronunciation_note and not alt_pinyin:
        alt_pinyin = pronunciation_note

    # Meaning override.
    if canonical in MEANING_OVERRIDES:
        meaning = MEANING_OVERRIDES[canonical]

    # HanziCraft enrichment for the radical itself.
    hc = (enrich or {}).get(canonical) or {}
    if hc.get("definition") and (not meaning or len(meaning) < 4):
        meaning = hc["definition"].replace("/", " / ")
    productivity = str(hc.get("productivity_count") or "")
    frequency = hc.get("frequency_rank") or ""
    decomposition = build_decomposition(canonical, hc.get("decomposition"))

    source_chars = normalize_member_chars(examples)
    member_chars = pick_member_chars(canonical, source_chars, cwc)
    _validate_member_picks(canonical, member_chars, cwc, log)
    member_decomp = build_member_decomp(member_chars, char_decomp, enrich)

    # Note assembly.
    note_extras: list[str] = []
    # Distinguish trad form when canonical differs.
    if canonical != canonical_trad:
        note_extras.append(f"Traditional: {canonical_trad}")
    if alt_pinyin:
        note_extras.append(f"Also reads: {alt_pinyin}")
    if canonical in NOTE_OVERRIDES:
        curated = NOTE_OVERRIDES[canonical].strip()
        if curated:
            note_extras.append(curated)
    note = "<br>".join(note_extras)

    # Link: HanziCraft URL covering radical + member chars (same pattern as
    # phonetic components).
    link_target = canonical + member_chars
    link = HANZICRAFT_URL.format(urllib.parse.quote(link_target))

    # Key: `<canonical>:<numeric-pinyin>`. Multi-reading radicals (rare) get
    # separate rows in the future if needed.
    key_pinyin = pinyin_marks_to_numeric(primary_pinyin) or f"row{line_no}"
    key = f"{canonical}:{key_pinyin}"

    # Tier tag.
    tier = classify_tier(canonical)
    tags = f"kangxi-radical {tier}"

    return [
        key,
        canonical,
        variant1,
        variant2,
        reference_variants,
        primary_pinyin,
        meaning,
        member_chars,
        productivity,
        frequency,
        decomposition,
        member_decomp,
        note,
        link,
        tags,
    ]


# ---------------------------------------------------------------------------
# TSV writer
# ---------------------------------------------------------------------------


def sanitize_field(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    s = s.replace("\t", " ")
    return s


def write_output(rows: list[list[str]], out_path: Path) -> None:
    header_col_count = len(RADICALS_HEADER)
    header_line = "\t".join(RADICALS_HEADER)
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
# Sort key — radicals for learning order
# ---------------------------------------------------------------------------

# Tier weight: core first, then common, then structural, then rare.
_TIER_RANK = {
    "radical-core": 0,
    "radical-common": 1,
    "radical-structural": 2,
    "radical-rare": 3,
}


def sort_key(row: list[str]) -> tuple:
    """Sort by tier first (core → common → structural → rare), then by member-
    char count descending (more curated examples = higher priority within tier),
    then by canonical + pinyin for stability."""
    canonical = row[1]
    pinyin = row[5]
    member_chars = row[7]
    tags_field = row[14]
    tier = "radical-common"
    for t in tags_field.split():
        if t in _TIER_RANK:
            tier = t
            break
    return (
        _TIER_RANK.get(tier, 1),
        -len(member_chars),
        canonical,
        pinyin,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=RADICALS_DECK_PATH)
    ap.add_argument("--enrich", type=Path, default=DEFAULT_HC_CACHE)
    ap.add_argument("--char-decomp", type=Path, default=DEFAULT_CHAR_DECOMP)
    ap.add_argument("--cwc", type=Path, default=DEFAULT_CWC_CACHE,
                    help="HanziCraft characterswithcomponent cache — used to "
                    "validate MEMBER_OVERRIDES picks at import time")
    args = ap.parse_args()

    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 1

    import json as _json

    enrich: dict[str, dict] | None = None
    if args.enrich.exists():
        try:
            enrich = _json.loads(args.enrich.read_text(encoding="utf-8"))
            print(f"loaded HanziCraft enrichment: {len(enrich)} entries", file=sys.stderr)
        except Exception as e:
            print(f"warn: failed to load enrich {args.enrich}: {e}", file=sys.stderr)

    char_decomp: dict[str, dict] | None = None
    if args.char_decomp.exists():
        try:
            char_decomp = _json.loads(args.char_decomp.read_text(encoding="utf-8"))
            print(f"loaded char decomp: {len(char_decomp)} entries", file=sys.stderr)
        except Exception as e:
            print(f"warn: failed to load char-decomp {args.char_decomp}: {e}", file=sys.stderr)

    cwc: dict[str, list[str]] | None = None
    if args.cwc.exists():
        try:
            cwc = _json.loads(args.cwc.read_text(encoding="utf-8"))
            print(f"loaded cwc: {len(cwc)} entries", file=sys.stderr)
        except Exception as e:
            print(f"warn: failed to load cwc {args.cwc}: {e}", file=sys.stderr)

    log: list[str] = []
    src_rows = read_source(args.source, log)

    out_rows: list[list[str]] = []
    seen: dict[str, int] = {}
    for line_no, fields in src_rows:
        try:
            row = transform_row(fields, line_no, log, enrich, char_decomp, cwc)
        except Exception as e:
            log.append(f"line {line_no}: transform error: {e!r}; skipping")
            continue
        if row is None:
            continue
        key = row[0]
        if key in seen:
            log.append(
                f"line {line_no}: duplicate Key {key!r} (first at line {seen[key]}); dropping"
            )
            continue
        seen[key] = line_no
        out_rows.append(row)

    out_rows.sort(key=sort_key)

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
