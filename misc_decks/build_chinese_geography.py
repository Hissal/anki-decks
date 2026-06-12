#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the improved "Chinese provinces and more" geography deck (CrowdAnki).

Source of truth = Chinese_Geography.tsv (human-editable, one row per place).
On first run the TSV is bootstrapped from the original deck.source.json plus the
capital / pinyin / fix tables below; thereafter the TSV is read back so manual
edits flow through.

Outputs (all into the deck folder):
  - deck.json        re-importable CrowdAnki deck (original GUIDs preserved, so a
                     re-import UPDATES the existing notes instead of duplicating)
  - styling.css      card CSS (also embedded in deck.json's note model)
  - TEMPLATES.md     the 6 front/back templates, for hand-editing inside Anki

Improvements over the original deck:
  - Capital now carries Chinese + pinyin (new fields), not just romanization.
  - Every card back shows the province identity block (hanzi / pinyin / audio)
    and, where relevant, the capital block -- even when not under test.
  - Two new card types: capital -> province, and capital reading (hanzi -> say it).
  - Pinyin is space-separated per syllable and tone-coloured by a small JS.
  - Traditional is kept as a back-only reference and auto-hidden when identical.
  - Data fixes: Macau simplified 澳门 (was traditional), bare names for
    Heilongjiang / Tibet, span-cruft stripped from hanzi fields.

Run:  python build_chinese_geography.py
Deps: standard library only.
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "知识__Geography__Chinese_provinces_and_more"
SRC_JSON = OUT_DIR / "deck.source.json"
TSV = OUT_DIR / "Chinese_Geography.tsv"
DECK_JSON = OUT_DIR / "deck.json"
CSS_FILE = OUT_DIR / "styling.css"
TEMPLATES_MD = OUT_DIR / "TEMPLATES.md"

_BASE91 = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "!#$%&()*+,-./:;<=>?@[]^_`{|}~"
)

# ---------------------------------------------------------------------------
# Note model
# ---------------------------------------------------------------------------

FIELDS = [
    "Map",
    "Name",
    "Name in simplified Chinese",
    "Name in traditional Chinese",
    "Name in pinyin",
    "Pronunciation",
    "Capital",
    "Capital in simplified Chinese",
    "Capital in pinyin",
    "Capital audio",
    "Etymology",
]
FIELD_SIZE = {
    "Map": 12, "Name": 20, "Name in simplified Chinese": 36,
    "Name in traditional Chinese": 26, "Name in pinyin": 20, "Pronunciation": 18,
    "Capital": 20, "Capital in simplified Chinese": 32, "Capital in pinyin": 20,
    "Capital audio": 18, "Etymology": 18,
}

CSS = """\
.card {
  font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", -apple-system, Arial, sans-serif;
  font-size: 20px;
  text-align: center;
  color: #1c1c1e;
  background: #fbfbfb;
  padding: 20px 14px;
  line-height: 1.4;
}
img { max-width: 90%; max-height: 340px; border-radius: 10px; }
#answer { border: 0; border-top: 2px solid #e3e3e3; margin: 18px auto; width: 80%; }

.prompt    { color: #6b7280; font-size: 17px; margin: 6px 0; }
.label     { color: #9aa0a6; font-size: 12px; letter-spacing: .08em;
             text-transform: uppercase; margin-top: 4px; }
.label.cap { color: #1a9e6e; }

.english   { font-size: 27px; font-weight: 700; margin: 4px 0; }
.hanzi     { font-size: 44px; font-weight: 600; margin: 6px 0; }
.hanzi-lg  { font-size: 64px; }
.hanzi.sm  { font-size: 30px; }
.pinyin    { font-size: 22px; margin: 3px 0; }
.pinyin-lg { font-size: 30px; }
.rom       { color: #9aa0a6; font-size: 16px; margin-top: 2px; }
.audio     { margin: 6px 0; }

.idblock   { margin-top: 10px; }
.idline    { margin: 2px 0; }
.trad      { color: #b07d2b; font-size: 16px; }
.tlabel    { opacity: .6; font-size: 11px; text-transform: uppercase; }

.capblock  { margin-top: 14px; padding-top: 10px; border-top: 1px dashed #e0e0e0; }
.sep       { height: 8px; }

.etymology { font-size: 18px; text-align: left; display: inline-block;
             max-width: 92%; line-height: 1.6; }
.etymology div { margin: 1px 0; }
[hidden]   { display: none; }

/* tone colours: 1 high, 2 rising, 3 low-dip, 4 falling, 5 neutral */
.t1 { color: #c0392b; }
.t2 { color: #d98014; }
.t3 { color: #1a9e3e; }
.t4 { color: #2a6fd6; }
.t5 { color: #8a8f98; }

/* night mode */
.nightMode.card  { background: #1e1f22; color: #e8e8ea; }
.nightMode #answer { border-top-color: #3a3b3e; }
.nightMode .prompt { color: #9aa0a6; }
.nightMode .rom    { color: #80858c; }
.nightMode .trad   { color: #d8a martin; }
.nightMode .t1 { color: #ff6b5e; }
.nightMode .t2 { color: #ffb454; }
.nightMode .t3 { color: #5fd07a; }
.nightMode .t4 { color: #6aa8ff; }
.nightMode .t5 { color: #9aa0a6; }
"""
# (the stray ".nightMode .trad" colour value is patched below before writing)
CSS = CSS.replace("#d8a martin;", "#d8a24a;")

# Small JS shared by every template: tone-colour every .pinyin block (per
# space-separated syllable) and hide the traditional form when it equals the
# simplified one.
JS = r"""
<script>
(function(){
  var T={'ā':1,'ē':1,'ī':1,'ō':1,'ū':1,'ǖ':1,
         'á':2,'é':2,'í':2,'ó':2,'ú':2,'ǘ':2,
         'ǎ':3,'ě':3,'ǐ':3,'ǒ':3,'ǔ':3,'ǚ':3,
         'à':4,'è':4,'ì':4,'ò':4,'ù':4,'ǜ':4};
  function tone(s){s=s.toLowerCase();for(var i=0;i<s.length;i++){if(T[s[i]]!=null)return T[s[i]];}return 5;}
  document.querySelectorAll('.pinyin').forEach(function(el){
    if(el.dataset.toned) return; el.dataset.toned='1';
    var txt=el.textContent.trim(); if(!txt) return;
    el.innerHTML=txt.split(/\s+/).map(function(s){
      return '<span class="t'+tone(s)+'">'+s+'</span>';
    }).join(' ');
  });
  document.querySelectorAll('.idline').forEach(function(l){
    var s=l.querySelector('.simp-han'), tr=l.querySelector('.trad'), th=l.querySelector('.trad-han');
    if(s&&tr&&th&&s.textContent.trim()===th.textContent.trim()) tr.style.display='none';
  });
})();
</script>"""

ANS = "{{FrontSide}}\n\n<hr id=answer>\n\n"

# province identity block (visible hanzi + trad + pinyin + audio)
IDENTITY = (
    '<div class="idblock">'
    '<div class="idline">'
    '<span class="hanzi simp-han">{{Name in simplified Chinese}}</span>'
    '<span class="trad"> <span class="tlabel">trad</span> '
    '<span class="trad-han">{{Name in traditional Chinese}}</span></span>'
    '</div>'
    '<div class="pinyin">{{Name in pinyin}}</div>'
    '<div class="audio">{{Pronunciation}}</div>'
    '</div>'
)
# identity block without the big hanzi (used when the front already shows it);
# carries a hidden simp-han so the trad auto-hide still works
IDENTITY_NOHAN = (
    '<div class="idblock">'
    '<div class="pinyin">{{Name in pinyin}}</div>'
    '<div class="audio">{{Pronunciation}}</div>'
    '<div class="idline">'
    '<span class="simp-han" hidden>{{Name in simplified Chinese}}</span>'
    '<span class="trad"><span class="tlabel">trad</span> '
    '<span class="trad-han">{{Name in traditional Chinese}}</span></span>'
    '</div>'
    '</div>'
)
# capital block on a province card's back (only when the place has a capital)
CAPBACK = (
    '{{#Capital in simplified Chinese}}'
    '<div class="capblock">'
    '<div class="label cap">capital</div>'
    '<div class="hanzi sm">{{Capital in simplified Chinese}}</div>'
    '<div class="pinyin">{{Capital in pinyin}}</div>'
    '<div class="rom">{{Capital}}</div>'
    '</div>'
    '{{/Capital in simplified Chinese}}'
)

# (name, qfmt, afmt) in display order
TEMPLATES = [
    (
        "maps",
        "{{Map}}",
        ANS + '<div class="english">{{Name}}</div>' + IDENTITY + CAPBACK + JS,
    ),
    (
        "locate",
        '<div class="prompt">Where is</div>'
        '<div class="english">{{Name}}</div>'
        '<div class="hanzi sm">{{Name in simplified Chinese}}</div>'
        '<div class="pinyin">{{Name in pinyin}}</div>'
        '<img src="_China_base.png">'
        + JS,
        '<div class="english">{{Name}}</div>'
        '<div class="hanzi sm">{{Name in simplified Chinese}}</div>'
        '<div class="pinyin">{{Name in pinyin}}</div>'
        '<hr id=answer>'
        '{{Map}}'
        + JS,
    ),
    (
        "capitals",
        '{{#Capital in simplified Chinese}}'
        '<div class="prompt">Capital of</div>'
        '<div class="english">{{Name}}</div>'
        '<div class="hanzi sm">{{Name in simplified Chinese}}</div>'
        '<div class="pinyin">{{Name in pinyin}}</div>'
        '{{/Capital in simplified Chinese}}'
        + JS,
        ANS
        + '<div class="label cap">capital</div>'
        + '<div class="hanzi">{{Capital in simplified Chinese}}</div>'
        + '<div class="pinyin">{{Capital in pinyin}}</div>'
        + '<div class="rom">{{Capital}}</div>'
        + '<div class="audio">{{Capital audio}}</div>'
        + JS,
    ),
    (
        "capital -> province",
        '{{#Capital in simplified Chinese}}'
        '<div class="hanzi hanzi-lg">{{Capital in simplified Chinese}}</div>'
        '<div class="pinyin">{{Capital in pinyin}}</div>'
        '<div class="rom">{{Capital}}</div>'
        '<div class="audio">{{Capital audio}}</div>'
        '<div class="prompt">&hellip; is the capital of which province?</div>'
        '{{/Capital in simplified Chinese}}'
        + JS,
        ANS + '<div class="english">{{Name}}</div>' + IDENTITY + JS,
    ),
    (
        "reading",
        '<div class="prompt">Which province / municipality?</div>'
        '<div class="hanzi hanzi-lg">{{Name in simplified Chinese}}</div>',
        ANS
        + '<div class="english">{{Name}}</div>'
        + IDENTITY_NOHAN
        + CAPBACK
        + JS,
    ),
    (
        "capital reading",
        '{{#Capital in simplified Chinese}}'
        '<div class="prompt">Read this capital</div>'
        '<div class="hanzi hanzi-lg">{{Capital in simplified Chinese}}</div>'
        '{{/Capital in simplified Chinese}}',
        ANS
        + '<div class="pinyin pinyin-lg">{{Capital in pinyin}}</div>'
        + '<div class="rom">{{Capital}}</div>'
        + '<div class="audio">{{Capital audio}}</div>'
        + '<div class="sep"></div><div class="label cap">capital of</div>'
        + '<div class="english">{{Name}}</div>'
        + '<div class="hanzi sm">{{Name in simplified Chinese}}</div>'
        + JS,
    ),
    (
        "etymology",
        '<div class="prompt">Etymology of</div>'
        '<div class="english">{{Name}}</div>'
        '<div class="hanzi sm">{{Name in simplified Chinese}}</div>'
        '<div class="pinyin">{{Name in pinyin}}</div>'
        + JS,
        ANS + '<div class="etymology">{{Etymology}}</div>' + JS,
    ),
]

# req: legacy "which fields make this card generate" (Anki recomputes, CrowdAnki
# keeps it). Capital cards are gated on the Capital-simplified field (ord 7).
REQ = [
    [0, "any", [0]],   # maps                -> Map
    [1, "any", [1]],   # locate              -> Name
    [2, "all", [7]],   # capitals            -> Capital simplified
    [3, "all", [7]],   # capital -> province -> Capital simplified
    [4, "any", [2]],   # reading             -> Name simplified
    [5, "all", [7]],   # capital reading     -> Capital simplified
    [6, "any", [10]],  # etymology           -> Etymology
]

# ---------------------------------------------------------------------------
# Data: per-place pinyin (space-separated), capitals, fixes, admin tags
# ---------------------------------------------------------------------------

NAME_PINYIN = {
    "Anhui": "Ān huī", "Chongqing": "Chóng qìng", "Fujian": "Fú jiàn",
    "Gansu": "Gān sù", "Guangdong": "Guǎng dōng", "Guangxi": "Guǎng xī",
    "Guizhou": "Guì zhōu", "Hainan": "Hǎi nán", "Hebei": "Hé běi",
    "Heilongjiang": "Hēi lóng jiāng", "Henan": "Hé nán", "Hong Kong": "Xiāng gǎng",
    "Hubei": "Hú běi", "Hunan": "Hú nán", "Inner Mongolia": "Nèi měng gǔ",
    "Jiangsu": "Jiāng sū", "Jiangxi": "Jiāng xī", "Jilin": "Jí lín",
    "Liaoning": "Liáo níng", "Macau": "Ào mén", "Ningxia": "Níng xià",
    "Qinghai": "Qīng hǎi", "Shaanxi": "Shǎn xī", "Shandong": "Shān dōng",
    "Shanghai": "Shàng hǎi", "Shanxi": "Shān xī", "Sichuan": "Sì chuān",
    "Tianjin": "Tiān jīn", "Tibet": "Xī zàng", "Xinjiang": "Xīn jiāng",
    "Yunnan": "Yún nán", "Zhejiang": "Zhè jiāng", "Beijing": "Běi jīng",
}

# Name -> (Capital romanized, Capital simplified, Capital pinyin spaced).
# Municipalities and SARs are their own seat -> left blank so no capital card.
CAPITALS = {
    "Anhui": ("Hefei", "合肥", "Hé féi"),
    "Fujian": ("Fuzhou", "福州", "Fú zhōu"),
    "Gansu": ("Lanzhou", "兰州", "Lán zhōu"),
    "Guangdong": ("Guangzhou", "广州", "Guǎng zhōu"),
    "Guangxi": ("Nanning", "南宁", "Nán níng"),
    "Guizhou": ("Guiyang", "贵阳", "Guì yáng"),
    "Hainan": ("Haikou", "海口", "Hǎi kǒu"),
    "Hebei": ("Shijiazhuang", "石家庄", "Shí jiā zhuāng"),
    "Heilongjiang": ("Harbin", "哈尔滨", "Hā ěr bīn"),
    "Henan": ("Zhengzhou", "郑州", "Zhèng zhōu"),
    "Hubei": ("Wuhan", "武汉", "Wǔ hàn"),
    "Hunan": ("Changsha", "长沙", "Cháng shā"),
    "Inner Mongolia": ("Hohhot", "呼和浩特", "Hū hé hào tè"),
    "Jiangsu": ("Nanjing", "南京", "Nán jīng"),
    "Jiangxi": ("Nanchang", "南昌", "Nán chāng"),
    "Jilin": ("Changchun", "长春", "Cháng chūn"),
    "Liaoning": ("Shenyang", "沈阳", "Shěn yáng"),
    "Ningxia": ("Yinchuan", "银川", "Yín chuān"),
    "Qinghai": ("Xining", "西宁", "Xī níng"),
    "Shaanxi": ("Xi'an", "西安", "Xī ān"),
    "Shandong": ("Jinan", "济南", "Jǐ nán"),
    "Shanxi": ("Taiyuan", "太原", "Tài yuán"),
    "Sichuan": ("Chengdu", "成都", "Chéng dū"),
    "Tibet": ("Lhasa", "拉萨", "Lā sà"),
    "Xinjiang": ("Ürümqi", "乌鲁木齐", "Wū lǔ mù qí"),
    "Yunnan": ("Kunming", "昆明", "Kūn míng"),
    "Zhejiang": ("Hangzhou", "杭州", "Háng zhōu"),
    # self-seat -> no capital card
    "Beijing": ("", "", ""),
    "Shanghai": ("", "", ""),
    "Tianjin": ("", "", ""),
    "Chongqing": ("", "", ""),
    "Hong Kong": ("", "", ""),
    "Macau": ("", "", ""),
}

HAN_SIMP_FIX = {"Macau": "澳门", "Heilongjiang": "黑龙江", "Tibet": "西藏"}
HAN_TRAD_FIX = {"Heilongjiang": "黑龍江", "Tibet": "西藏"}

ETYM_APPEND = {
    "Heilongjiang": '<div>Official form: 黑龙江省 (-shěng, &ldquo;province&rdquo;).</div>',
    "Tibet": '<div>Official form: 西藏自治区 Xīzàng Zìzhìqū (&ldquo;autonomous region&rdquo;).</div>',
}

PROVINCES = {
    "Anhui", "Fujian", "Gansu", "Guangdong", "Guizhou", "Hainan", "Hebei",
    "Heilongjiang", "Henan", "Hubei", "Hunan", "Jiangsu", "Jiangxi", "Jilin",
    "Liaoning", "Qinghai", "Shaanxi", "Shandong", "Shanxi", "Sichuan", "Yunnan",
    "Zhejiang",
}
AUTONOMOUS = {"Guangxi", "Inner Mongolia", "Ningxia", "Tibet", "Xinjiang"}
MUNICIPALITY = {"Beijing", "Shanghai", "Tianjin", "Chongqing"}
SAR = {"Hong Kong", "Macau"}


def admin_tag(name: str) -> str:
    if name in PROVINCES:
        kind = "province"
    elif name in AUTONOMOUS:
        kind = "autonomous-region"
    elif name in MUNICIPALITY:
        kind = "municipality"
    elif name in SAR:
        kind = "sar"
    else:
        kind = "other"
    return "china-geography " + kind


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_han(s: str) -> str:
    """Strip HTML tags / nbsp from a hanzi field, leaving bare characters."""
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\xa0", "").replace("&nbsp;", "")
    return s.strip()


def guid_fallback(name: str) -> str:
    """Deterministic guid for any future place not in the original deck."""
    num = int(hashlib.sha256(("zh-geo-v1:" + name).encode()).hexdigest(), 16)
    out = ""
    while num and len(out) < 10:
        num, rem = divmod(num, 91)
        out = _BASE91[rem] + out
    return out.rjust(10, _BASE91[0])


def build_rows_from_source(src: dict) -> list[dict]:
    """Bootstrap rows from the original 8-field deck + the data tables above."""
    missing = [n["fields"][1].strip() for n in src["notes"]
               if n["fields"][1].strip() not in NAME_PINYIN
               or n["fields"][1].strip() not in CAPITALS]
    if missing:
        raise SystemExit("Missing pinyin/capital data for: " + ", ".join(missing))

    rows = []
    for n in src["notes"]:
        f = n["fields"]
        name = f[1].strip()
        cap_en, cap_simp, cap_py = CAPITALS[name]
        rows.append({
            "Map": f[0],
            "Name": name,
            "Name in simplified Chinese": HAN_SIMP_FIX.get(name, clean_han(f[2])),
            "Name in traditional Chinese": HAN_TRAD_FIX.get(name, clean_han(f[3])),
            "Name in pinyin": NAME_PINYIN[name],
            "Pronunciation": f[5],
            "Capital": cap_en,
            "Capital in simplified Chinese": cap_simp,
            "Capital in pinyin": cap_py,
            "Capital audio": "",  # filled later by the user (TTS)
            "Etymology": f[7] + ETYM_APPEND.get(name, ""),
            "Tags": admin_tag(name),
        })
    return rows


def write_tsv(rows: list[dict]) -> None:
    cols = FIELDS + ["Tags"]
    lines = [
        "#separator:tab",
        "#html:true",
        "#columns:" + "\t".join(cols),
        "#tags column:%d" % len(cols),
    ]
    for r in rows:
        cells = [r[c].replace("\t", " ").replace("\n", " ") for c in cols]
        lines.append("\t".join(cells))
    TSV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_tsv() -> list[dict]:
    """Read rows mapping cells by the file's own #columns header, so adding a
    field to FIELDS never shifts/corrupts an older TSV (missing cols -> '')."""
    want = FIELDS + ["Tags"]
    file_cols = None
    data = []
    for line in TSV.read_text(encoding="utf-8").splitlines():
        if line.startswith("#columns:"):
            file_cols = line[len("#columns:"):].split("\t")
        elif line and not line.startswith("#"):
            data.append(line.split("\t"))
    if file_cols is None:
        file_cols = list(want)
    rows = []
    for cells in data:
        cells += [""] * (len(file_cols) - len(cells))
        by_name = {file_cols[i]: cells[i] for i in range(len(file_cols))}
        rows.append({c: by_name.get(c, "") for c in want})
    return rows


def build_deck(src: dict, rows: list[dict]) -> dict:
    guid_by_name = {n["fields"][1].strip(): n["guid"] for n in src["notes"]}
    model = src["note_models"][0]
    model_uuid = model["crowdanki_uuid"]

    model["flds"] = [{
        "collapsed": False, "description": "", "excludeFromSearch": False,
        "font": "Arial", "id": None, "media": [], "name": name, "ord": i,
        "plainText": False, "preventDeletion": False, "rtl": False,
        "size": FIELD_SIZE[name], "sticky": False, "tag": None,
    } for i, name in enumerate(FIELDS)]

    model["tmpls"] = [{
        "afmt": afmt, "bafmt": "", "bfont": "", "bqfmt": "", "bsize": 0,
        "did": None, "id": None, "name": name, "ord": i, "qfmt": qfmt,
    } for i, (name, qfmt, afmt) in enumerate(TEMPLATES)]

    model["css"] = CSS
    model["req"] = REQ
    model["sortf"] = 1  # sort browser rows by Name

    notes = []
    for r in rows:
        name = r["Name"].strip()
        notes.append({
            "__type__": "Note",
            "fields": [r[f] for f in FIELDS],
            "guid": guid_by_name.get(name) or guid_fallback(name),
            "note_model_uuid": model_uuid,
            "tags": r["Tags"].split(),
        })
    src["notes"] = notes

    media = src.get("media_files", [])
    if "_China_base.png" not in media:
        media.append("_China_base.png")
    src["media_files"] = sorted(media)
    return src


def write_templates_md() -> None:
    out = ["# Card templates — Chinese Geography\n",
           "Paste each Front/Back into Anki › Tools › Manage Note Types › "
           "*ChinaProvinces* › Cards. Styling lives in `styling.css`.\n"]
    for i, (name, qfmt, afmt) in enumerate(TEMPLATES, 1):
        out.append(f"\n## Card {i} — {name}\n")
        out.append("**Front**\n\n```html\n" + qfmt + "\n```\n")
        out.append("**Back**\n\n```html\n" + afmt + "\n```\n")
    TEMPLATES_MD.write_text("\n".join(out), encoding="utf-8")


def main() -> None:
    src = json.loads(SRC_JSON.read_text(encoding="utf-8"))

    if TSV.exists():
        rows = read_tsv()
        origin = "Chinese_Geography.tsv (existing)"
    else:
        rows = build_rows_from_source(src)
        origin = "bootstrapped from deck.source.json"
    write_tsv(rows)  # always re-emit so the TSV matches the current column schema

    deck = build_deck(src, rows)
    DECK_JSON.write_text(
        json.dumps(deck, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    CSS_FILE.write_text(CSS, encoding="utf-8")
    write_templates_md()

    caps = sum(1 for r in rows if r["Capital in simplified Chinese"].strip())
    print("Chinese Geography deck built.")
    print("  rows        :", len(rows), "(source:", origin + ")")
    print("  with capital:", caps, "/", len(rows))
    print("  templates   :", len(TEMPLATES))
    print("  fields      :", len(FIELDS))
    print("  wrote       : deck.json, Chinese_Geography.tsv, styling.css, TEMPLATES.md")


if __name__ == "__main__":
    main()
