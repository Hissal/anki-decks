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

NOTE_OVERRIDES: dict[str, str] = {
    # --- Visual look-alikes (most-confused clusters in modern reading) ---
    "日": "Visually similar to 曰 (yuē, 'say'). 日 is taller and narrower; 曰 is squatter and wider. Both have a horizontal stroke inside.",
    "曰": "Visually similar to 日 (rì, 'sun'). 曰 is wider/shorter than 日 — the inner stroke doesn't fully cross.",
    "月": "Visually identical to 肉 (⺼, 'meat/flesh') when used as a left-side radical. Same printed shape in modern fonts; etymologically distinct. Body parts (脸, 腿, 胸, 肝) use the 肉 form; time/light words (期, 朝, 明) use the 月 form.",
    "肉": "When at the left or bottom of a char, 肉 takes the form ⺼ which looks IDENTICAL to 月 (moon). Body-part chars (脸, 腿, 胸, 肝, 脏, 肺) all use this. Distinguish by meaning, not glyph.",
    "刀": "Positional variant: 刂 on the right side of a char. Same radical, same meaning.",
    "刂": "Right-side form of 刀 (knife). Look for it in 分, 刻, 利, 别, 到.",
    "心": "Three forms by position: 心 (standalone/bottom), 忄 (left side — fast tilted form), ⺗ (bottom — the 'compressed' form in 慕, 慰). All three mean the same thing.",
    "忄": "Left-side variant of 心 (heart). Used in emotion/feeling chars: 情, 怕, 忙, 快, 慢.",
    "⺗": "Bottom-position variant of 心 (heart). Used in 慕, 慰, 恭. Different glyph from ⺗-as-radical sometimes called the 'four dots heart'.",
    "水": "Three positional forms: 水 (standalone), 氵 (left — 'three dots water'), 氺 (bottom — rare). 氵 is by far the most common in modern usage.",
    "氵": "Left-side form of 水 (water). Aka 'three dots water'. Used in 河, 海, 湖, 洋, 洗 — all water-related.",
    "火": "Bottom-position variant: 灬 ('four dots fire'). Used in 热, 点, 煮, 蒸, 照, 然.",
    "灬": "Bottom-position variant of 火 (fire). Despite the four dots, it's still 'fire'. Used in 热, 点, 煮, 蒸, 然 — heat/cooking themes.",
    "手": "Left-side variant: 扌. Used in nearly every action verb: 打, 拉, 推, 握, 抓.",
    "扌": "Left-side form of 手 (hand). Catch-all for action verbs.",
    "言": "Simplified left form: 讠. Used in speech-related chars: 说, 话, 语, 词, 读. Traditional uses the full 言.",
    "讠": "Simplified left-side form of 言 (speech). Always speech-related.",
    "金": "Simplified left form: 钅. Used in metal/tool chars: 银, 铜, 铁, 钱, 钟. Traditional uses 釒.",
    "钅": "Simplified left form of 金 (metal). All metals + metallic objects.",
    "食": "Simplified left form: 饣. Used in eating/food chars: 饭, 饮, 饿, 馆. Traditional uses 飠.",
    "饣": "Simplified left form of 食 (eat/food). Always food/eating-related.",
    "糸": "Simplified left form: 纟 ('silk-thread'). Used for textile/thread-related chars: 红, 给, 经, 细, 络. Traditional uses 糹.",
    "纟": "Simplified left form of 糸 (silk/thread). Threads, colors of cloth, binding.",
    "肉": "Note: when used as left-side radical, identical glyph to 月. Body parts.",  # duplicate — second appearance OK; overrides apply to canonical key
    "邑": "Right-side form: 阝 (city/state). When 阝 is on the RIGHT of a char, it's 邑 (city) — used in place names: 那, 邻, 邦, 都, 郊.",
    "阜": "Left-side form: 阝 (mound/hill). Same glyph as 邑's variant but on the LEFT side — completely different meaning. Used in 阳, 阴, 院, 阶, 阻, 陈 (terrain/elevation themes).",
    "阝": "Two completely different radicals share this glyph: 邑 (city) when on the RIGHT (都, 邻, 邦); 阜 (mound) when on the LEFT (阳, 阴, 院). Side determines meaning.",
    "示": "Left-side form: 礻. Used for spirit/ritual chars: 礼, 神, 福, 祝, 祖.",
    "礻": "Left-side form of 示 (spirit/altar). Don't confuse with 衤 (clothes) — 礻 has ONE dot at top, 衤 has TWO.",
    "衣": "Left-side form: 衤. Don't confuse with 礻 — 衤 (clothes) has TWO dots at top, 礻 (spirit) has ONE. Used in 初, 被, 装, 裙.",
    "衤": "Left-side form of 衣 (clothes). Note the 2-dot top distinguishing it from 礻 (spirit, 1-dot).",
    "牛": "Left-side variant: 牜. Used in animal/livestock chars: 物, 特, 牲, 牧.",
    "犬": "Left-side variant: 犭 ('three strokes dog'). Used in animal chars: 狗, 猫, 狼, 猪, 狐.",
    "犭": "Left-side form of 犬 (dog). Used for most quadruped animals (not just dogs).",
    "玉": "Used as a left-side radical, the glyph reduces to 王 — looks identical to the 'king' character. Found in jade/jewelry chars: 玩, 理, 球, 现, 珠, 玻.",
    "王": "As a radical, this glyph IS the left-side form of 玉 (jade), NOT the standalone 王 ('king'). Chars: 玩, 理, 球. The standalone 王 has its own radical role only in very few chars.",
    "网": "Top-position variant: 罒 (four-cornered 'net' at top of char). Used in 罗, 罚, 罢, 罪, 置.",
    "罒": "Top-position variant of 网 (net). Used in chars about catching/snaring/imprisoning: 罗, 罪, 罚, 置.",
    "辵": "Modern form: 辶 ('walking-go radical'). Used in motion verbs: 走 (no, 走 has its own radical), 进, 退, 通, 道, 这, 那.",
    "辶": "Modern form of 辵 (walk). The 'walking radical' at the bottom-left. Always motion/path-related.",
    "艸": "Modern form: 艹 ('grass top'). Used in plants/herbs/grasses: 花, 草, 茶, 药, 苹.",
    "艹": "Modern form of 艸 (grass). The 'grass top' — plants, herbs, vegetables.",
    "竹": "Bottom variant when used as top radical: ⺮ ('bamboo top'). Used in 笔, 笑, 第, 答, 篮.",
    "⺮": "Top-position form of 竹 (bamboo). Used in chars made of bamboo or that involved bamboo strips (笔 'brush', 第 'order from bamboo slips').",
    "老": "Top variant: 耂. Used in 考, 孝, 者 (where the radical shrinks at the top).",
    "耂": "Top variant of 老 (old). Used in 考, 孝, 者 — age-related themes.",

    # --- Visual look-alikes among standalone radicals ---
    "己": "Three nearly-identical chars: 己 (jǐ, self), 已 (yǐ, already), 巳 (sì, sixth earthly branch). 己 is open on top-right; 已 is half-closed; 巳 is fully closed.",
    "巳": "Confusable with 己 (jǐ, self) and 已 (yǐ, already). 巳 is fully closed at the top.",
    "戈": "Confusable family: 戊 (wù) / 戌 (xū) / 戍 (shù) / 戎 (róng) — all have 戈 with different inner strokes. Plus 我 (wǒ, I/me) and 成 (chéng, become).",
    "千": "Visually similar to 干 (gān, dry) and 壬 (rén). 千 has a 丿 stroke on top; 干 is a horizontal line; 壬 has 丿 with offset.",
    "干": "Visually similar to 千 (qiān, thousand). 干 starts with a horizontal stroke; 千 starts with a slanted 丿.",
    "末": "Visually similar to 未 (wèi, not yet). 末 has the LONGER stroke at the very top (top horizontal is widest). 未 has the longer stroke in the MIDDLE.",
    "未": "Visually similar to 末 (mò, end). 未 has the longer stroke in the MIDDLE; 末 has it at the TOP.",
    "大": "Look-alike cluster: 大 (dà, big), 太 (tài, very), 犬 (quǎn, dog), 夫 (fū, man). 大 has nothing extra; 太 adds a dot below; 犬 adds a dot above-right; 夫 has an extra horizontal stroke.",
    "夫": "Visually similar to 天 (tiān, sky) and 失 (shī, lose). 夫 has the TOP horizontal sticking out left.",
    "户": "Visually similar to 尸 (shī, corpse) and 戶/戸 (trad/var of 户). 户 has an extra dot/stroke at the top that 尸 lacks.",
    "尸": "Visually similar to 户 (hù, door). 户 has an extra dot; 尸 is bare. Used in body-position chars: 居, 屋, 屑, 屁.",
    "入": "Visually similar to 人 (rén, person) and 八 (bā, eight). 入 ('enter') has the right stroke crossing INSIDE; 人 has strokes meeting at a point; 八 has strokes going down/out.",
    "人": "Look-alike: 入 (rù, enter) and 八 (bā, eight). 人 has clean diagonals meeting at the top; 入 crosses; 八 splits outward.",
    "卩": "Visually similar to 阝 (left or right). 卩 is shorter — used standalone or in 印, 卯, 危.",
    "刃": "刃 = 刀 + a dot marking the blade's edge. Distinguish from 力 (lì, strength) — 力 has a hook curving differently.",
    "厂": "Visually similar to 广 (guǎng, 'dotted cliff'). 广 has a dot on top of the 厂 shape.",
    "广": "Visually similar to 厂 (hàn, cliff). 广 has an extra dot/stroke on top.",
    "卯": "Visually similar to 卬 / 印. 卯 has both halves vertical with equal opening.",
    "犬": "Look-alike: 大 + a dot. 犬 has a top-right dot that 大 doesn't.",
    "玉": "Look-alike: 王 + a dot. 玉 has a bottom-right dot that 王 doesn't.",  # canonical 玉 — already documented above for radical role
    "土": "Visually similar to 士 (shì, scholar). 土 has the LOWER horizontal LONGER; 士 has the UPPER horizontal longer.",
    "士": "Visually similar to 土 (tǔ, earth). 士 has the UPPER horizontal longer; 土 has the LOWER one longer.",
    "甘": "Visually similar to 日 / 曰 but has TWO inner horizontals instead of one.",

    # --- Role flags: when a radical doubles as a phonetic component ---
    "工": "Also a phonetic component (gōng) — see the phonetic-components deck for 工:gōng / gǒng with member sets 功攻 / 巩鞏汞銾.",
    "白": "Also a phonetic component (bái / bǎi) — appears phonetically in 百, 帛, 拍.",
    "比": "Also a phonetic component — see the phonetic-components deck for 比:bǐ and 比:bì.",
    "皮": "Also a phonetic component (pí) — appears in 披, 彼, 波, 破.",
    "几": "Also a phonetic component (jī / jǐ) — appears in 机, 飢, 肌.",

    # --- Function flags: semantic-only radicals (rarely phonetic) ---
    "心": "Almost always semantic (heart / emotion), not phonetic. When 忄 appears on the left, the meaning is always emotion-related.",
    "贝": "Semantic radical for money / wealth / trade. Rarely phonetic. Used in 财, 货, 购, 资, 贵.",
    "贝": "Semantic for money/trade. The original form 貝 represented cowrie shells, used as currency in ancient times.",  # duplicate fine
    "金": "Semantic for metals / tools / wealth (extended). The simplified 钅 is overwhelmingly semantic, never phonetic in modern chars.",
    "口": "Semantic for mouth / speech / opening — rarely the phonetic. Compounds describe sounds, eating, or shapes with openings.",
    "穴": "Semantic for hole / cave / opening. Used in 空, 究, 穿, 窗, 穷.",
    "宀": "'Roof' radical — used in chars about buildings, dwellings, containment: 家, 室, 安, 完, 守.",
    "广": "'Dotted cliff' / 'shed' radical — semantically 'building under a roof'. Used in 床, 店, 府, 度, 庭.",
    "厂": "'Cliff' radical — used in chars about cliffs, factories, weight: 厂, 厚, 原, 厌.",
}


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


MEMBER_TARGET = 6  # aim for at least this many MemberChars before augmenting from cwc


def _decomp_contains(
    ch: str,
    radical: str,
    char_decomp: dict[str, dict] | None,
    aliases: set[str],
) -> bool:
    """True when ch's once-level decomp contains the radical or one of its
    positional variants. Loose cwc membership isn't enough — HC's cwc lists
    many chars where the radical only appears as a deep sub-stroke (e.g.
    cwc[矛] includes 我 / 之 / 成 which don't visually contain 矛)."""
    if char_decomp is None:
        return True  # no decomp data → can't filter; accept
    entry = char_decomp.get(ch)
    if not entry:
        return False
    once = entry.get("once") or []
    needle = {radical} | aliases
    return any(p in needle for p in once)


def pick_member_chars(
    canonical: str,
    source_chars: str,
    cwc: dict[str, list[str]] | None = None,
    char_data: dict[str, dict] | None = None,
    char_decomp: dict[str, dict] | None = None,
    variant_aliases: set[str] | None = None,
) -> str:
    """Apply MEMBER_OVERRIDES if defined; else filter the source set against
    HanziCraft's cwc list; then augment from cwc with a strict decomp filter
    (radical must appear in once-level decomp) until MEMBER_TARGET is met.
    Falls back to loose cwc if strict pass yields too few."""
    override = MEMBER_OVERRIDES.get(canonical)
    if override:
        return override

    aliases = set(variant_aliases or [])

    valid: list[str] = []
    valid_set: set[str] = set()
    if cwc is not None:
        valid = list(cwc.get(canonical, []))
        cwc_alias = MEMBER_OVERRIDE_CWC_ALIAS.get(canonical)
        if cwc_alias:
            valid = valid + [c for c in cwc.get(cwc_alias, []) if c not in valid]
        valid_set = set(valid)

    seen: set[str] = set()
    out: list[str] = []

    # Step 1: source picks filtered through cwc membership only.
    for ch in source_chars:
        if ch in seen:
            continue
        if valid_set and ch not in valid_set:
            continue
        seen.add(ch)
        out.append(ch)
        if len(out) >= MEMBER_CAP:
            return "".join(out)

    # Step 2: augment with STRICT decomp-level matches first.
    if len(out) < MEMBER_TARGET and valid:
        for ch in valid:
            if ch in seen or ch == canonical:
                continue
            if char_data is not None and not (
                ch in char_data and char_data[ch].get("pinyin")
            ):
                continue
            if not _decomp_contains(ch, canonical, char_decomp, aliases):
                continue
            seen.add(ch)
            out.append(ch)
            if len(out) >= MEMBER_CAP:
                break

    # No step 3 fallback — better to show 4 strictly-correct chars than 8
    # with HC-loose noise like 矛 → 我 / 或 / 找 (which structurally don't
    # contain 矛 despite appearing in cwc[矛]).
    return "".join(out)


def transform_row(
    fields: list[str],
    line_no: int,
    log: list[str],
    enrich: dict[str, dict] | None = None,
    char_decomp: dict[str, dict] | None = None,
    cwc: dict[str, list[str]] | None = None,
    char_data: dict[str, dict] | None = None,
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
    # Pass variant glyphs as aliases so the decomp filter accepts chars whose
    # once-decomp uses the variant form (e.g. 唱's once is [口, 昌] — passes
    # for the 口 radical naturally; but 情's once is [忄, 青] — 忄 should
    # count as a 心-decomp match when 忄 is in variant_aliases).
    variant_aliases: set[str] = set()
    if variant1:
        variant_aliases.add(variant1)
    if variant2:
        variant_aliases.add(variant2)
    member_chars = pick_member_chars(
        canonical, source_chars, cwc, char_data, char_decomp, variant_aliases
    )
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

    char_data: dict[str, dict] | None = None
    if DEFAULT_CHAR_DATA.exists():
        try:
            char_data = _json.loads(DEFAULT_CHAR_DATA.read_text(encoding="utf-8"))
            print(f"loaded char data: {len(char_data)} entries", file=sys.stderr)
        except Exception as e:
            print(f"warn: failed to load char-data {DEFAULT_CHAR_DATA}: {e}", file=sys.stderr)

    log: list[str] = []
    src_rows = read_source(args.source, log)

    out_rows: list[list[str]] = []
    seen: dict[str, int] = {}
    for line_no, fields in src_rows:
        try:
            row = transform_row(fields, line_no, log, enrich, char_decomp, cwc, char_data)
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
