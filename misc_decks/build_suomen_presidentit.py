#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the expanded "Suomen Presidentit" deck from deck.source.json.

Idempotent: always starts from deck.source.json. Normalizes the scraped HTML
(Years/Info/Party/Name), merges curated Finnish enrichment
(suomen_presidentit_data.ENRICH), computes predecessor/successor, installs the 14
difficulty-ordered per-president templates + two aggregate note types (party
rosters, a JS tap-reveal recite card, trivia), and writes deck.json with stable
ids + deterministic guids so re-runs produce no diff.

Pattern mirrors misc_decks/build_finland_subdivisions.py. Stdlib only at runtime.
"""

import base64
import copy
import hashlib
import html as html_mod
import json
import re
from pathlib import Path

from suomen_presidentit_data import ENRICH, PARTY_CANON, TRIVIA

OUT_DIR = Path(__file__).resolve().parent / "Suomen_presidentit"
SRC = OUT_DIR / "deck.source.json"
OUT = OUT_DIR / "deck.json"

_TAG_RE = re.compile(r"<[^>]+>")
_YEAR_RE = re.compile(r"(\d{4})")


# --------------------------------------------------------------------------- #
# Normalization helpers
# --------------------------------------------------------------------------- #
def _strip_tags(s: str) -> str:
    """Remove HTML tags, decode entities, drop nbsp -> plain text."""
    return html_mod.unescape(_TAG_RE.sub("", s)).replace("\xa0", " ").strip()


def normalize_years(raw: str) -> str:
    """Scraped term string -> 'YYYY–YYYY', '… †' if died in office, 'YYYY–' if current."""
    died = "†" in raw
    current = "-&gt;" in raw or "->" in raw or "–&gt;" in raw
    text = _strip_tags(raw)
    years = _YEAR_RE.findall(text)
    if not years:
        return text
    start = years[0]
    if current:
        return f"{start}–"
    end = years[-1] if len(years) > 1 else ""
    out = f"{start}–{end}" if end else f"{start}–"
    return f"{out} †" if died else out


def normalize_info(raw: str) -> str:
    """Strip <sup> citations + table wrappers, collapse whitespace, keep prose."""
    without_sup = re.sub(r"<sup>.*?</sup>", "", raw, flags=re.DOTALL)
    text = _strip_tags(without_sup)
    return re.sub(r"\s+", " ", text).strip()


def canon_party(raw: str) -> str:
    """Map a scraped party string to its canonical display name."""
    return PARTY_CANON.get(raw.strip(), raw.strip())


def compute_neighbors(rows):
    """rows = [(ordinal:int, name:str), ...]. Returns (pred, succ) dicts keyed by
    ordinal; value is 'Name (N.)' or '' at the ends."""
    rows = sorted(rows)
    pred, succ = {}, {}
    for i, (ordn, name) in enumerate(rows):
        pred[ordn] = f"{rows[i-1][1]} ({rows[i-1][0]}.)" if i > 0 else ""
        succ[ordn] = f"{rows[i+1][1]} ({rows[i+1][0]}.)" if i < len(rows) - 1 else ""
    return pred, succ


# --------------------------------------------------------------------------- #
# Per-president note model
# --------------------------------------------------------------------------- #
# Appended after the original 6 fields (Ordinal, Name, Years, Image, Party, Info).
NEW_FIELDS = ["Life", "Profession", "Birthplace", "KnownFor", "Nickname", "Link",
              "Predecessor", "Successor"]
_NEW_FIELD_ID_BASE = 800000000  # stable ids for the appended fields

# (template name, front HTML, req-kind, req-field-name). Difficulty-graded order.
CARDS = [
    ("Image → Name",       '{{Image}}<div class="ask">Kuka?</div>', "any", "Image"),
    ("KnownFor → Name",    '<div class="clue">{{KnownFor}}</div><div class="ask">Kuka presidentti?</div>', "any", "KnownFor"),
    ("Nickname → Name",    '<div class="clue">”{{Nickname}}”</div><div class="ask">Kuka presidentti?</div>', "any", "Nickname"),
    ("Years → Name",       '<div class="clue">{{Years}}</div><div class="ask">Kuka oli presidentti?</div>', "any", "Years"),
    ("Ordinal → Name",     '<div class="clue">{{Ordinal}} presidentti</div><div class="ask">Kuka?</div>', "any", "Ordinal"),
    ("Name → Ordinal",     '{{Name}}<div class="ask">Mones presidentti?</div>', "all", "Ordinal"),
    ("Name → Party",       '{{Name}}<div class="ask">Mikä puolue?</div>', "all", "Party"),
    ("Name → KnownFor",    '{{Name}}<div class="ask">Mistä tunnettu?</div>', "all", "KnownFor"),
    ("Name → Profession",  '{{Name}}<div class="ask">Ammatti ennen presidenttiyttä?</div>', "all", "Profession"),
    ("Name → Birthplace",  '{{Name}}<div class="ask">Syntymäpaikka?</div>', "all", "Birthplace"),
    ("Name → Predecessor", '{{Name}}<div class="ask">Edeltäjä?</div>', "all", "Predecessor"),
    ("Name → Successor",   '{{Name}}<div class="ask">Seuraaja?</div>', "all", "Successor"),
    ("Name → Years",       '{{Name}}<div class="ask">Toimikausi?</div>', "all", "Years"),
    ("Name → Life",        '{{Name}}<div class="ask">Elinvuodet?</div>', "all", "Life"),
]

# Context table shown on every per-president back.
PROFILE_TABLE = """<table class="profile">
<tr><th>Järjestys</th><td>{{Ordinal}}</td></tr>
<tr><th>Toimikausi</th><td>{{Years}}</td></tr>
<tr><th>Puolue</th><td>{{Party}}</td></tr>
{{#Life}}<tr><th>Elinvuodet</th><td>{{Life}}</td></tr>{{/Life}}
{{#Profession}}<tr><th>Ammatti</th><td>{{Profession}}</td></tr>{{/Profession}}
{{#Birthplace}}<tr><th>Syntymäpaikka</th><td>{{Birthplace}}</td></tr>{{/Birthplace}}
{{#Nickname}}<tr><th>Lempinimi</th><td>{{Nickname}}</td></tr>{{/Nickname}}
{{#KnownFor}}<tr><th>Tunnettu</th><td>{{KnownFor}}</td></tr>{{/KnownFor}}
{{#Predecessor}}<tr><th>Edeltäjä</th><td>{{Predecessor}}</td></tr>{{/Predecessor}}
{{#Successor}}<tr><th>Seuraaja</th><td>{{Successor}}</td></tr>{{/Successor}}
</table>"""


def build_back(answer_field: str) -> str:
    """Per-card back: the tested answer big + highlighted at the top, profile below.

    Reverse cards (answer == Name) highlight the name itself; forward cards show
    the name small as context above the highlighted answer, so the thing you were
    actually tested on is immediately visible without hunting the table.
    """
    who = "" if answer_field == "Name" else '<div class="who">{{Name}}</div>\n'
    return (
        "{{FrontSide}}\n<hr id=answer>\n"
        + who
        + '<div class="answer">{{%s}}</div>\n' % answer_field
        + '{{#Image}}<div class="pic">{{Image}}</div>{{/Image}}\n'
        + PROFILE_TABLE + "\n"
        + '{{#Info}}<div class="info">{{Info}}</div>{{/Info}}\n'
        + '{{#Link}}<div class="src"><a href="{{Link}}">Lue lisää Wikipediasta →</a></div>{{/Link}}'
    )

PRES_CSS = """.card { font-family: arial; font-size: 20px; line-height: 1.5;
  text-align: center; color: black; background-color: white; }
.ask { color: #555; font-size: 16px; margin-top: .6em; }
.clue { font-size: 24px; }
.who { font-size: 17px; color: #666; }
.answer { display: inline-block; font-size: 25px; font-weight: bold;
  padding: 2px 12px; border-radius: 6px; background: #fff3c4; color: #222;
  margin: .2em 0 .45em; }
.pic img { max-height: 200px; }
table.profile { margin: .5em auto; border-collapse: collapse; text-align: left; }
table.profile th { color: #777; font-weight: normal; padding: 2px 10px 2px 0;
  vertical-align: top; white-space: nowrap; }
table.profile td { padding: 2px 0; }
.info { font-size: 15px; color: #555; margin: .6em auto 0; max-width: 36em;
  text-align: left; }
.hint { color: #777; font-size: 14px; }
.src { margin-top: .7em; }
.src a { color: #06c; font-size: 14px; text-decoration: none; }
#reciteList { display: inline-block; text-align: left; margin: .5em auto; }
#reciteList li { margin: 5px 0; font-size: 19px; }
#reciteList summary { cursor: pointer; color: #06c; }
#reciteList details[open] summary { display: none; }
#reciteList details[open] { font-weight: bold; }
/* Night mode: lift muted greys + accents so they stay readable on dark. */
.nightMode .ask { color: #b8b8b8; }
.nightMode .who { color: #bbb; }
.nightMode .answer { background: #4a4326; color: #ffe9a8; }
.nightMode table.profile th { color: #aaa; }
.nightMode .info { color: #cfcfcf; }
.nightMode .hint { color: #b0b0b0; }
.nightMode .src a, .nightMode #reciteList summary { color: #6af; }"""


def build_president_model(src_model: dict) -> dict:
    """Return the expanded per-president note model (fields, 14 templates, req, css)."""
    model = copy.deepcopy(src_model)

    flds = model["flds"]
    base_ord = len(flds)
    proto_field = copy.deepcopy(flds[0])
    for i, fname in enumerate(NEW_FIELDS):
        f = copy.deepcopy(proto_field)
        f["name"] = fname
        f["ord"] = base_ord + i
        f["id"] = _NEW_FIELD_ID_BASE + i
        flds.append(f)

    idx = {f["name"]: f["ord"] for f in flds}

    proto_tmpl = copy.deepcopy(model["tmpls"][0])
    tmpls, req = [], []
    for ordn, (name, front, kind, field) in enumerate(CARDS):
        t = copy.deepcopy(proto_tmpl)
        t["name"] = name
        t["ord"] = ordn
        t["id"] = 900000000 + ordn
        t["qfmt"] = front
        t["afmt"] = build_back(field if name.startswith("Name →") else "Name")
        t["bqfmt"] = ""
        t["bafmt"] = ""
        tmpls.append(t)
        req.append([ordn, kind, [idx[field]]])

    model["tmpls"] = tmpls
    model["req"] = req
    model["css"] = PRES_CSS
    model["sortf"] = idx["Name"]
    return model


# --------------------------------------------------------------------------- #
# Aggregate note types + generated notes
# --------------------------------------------------------------------------- #
KOONTI_UUID = "7f3a9c20-5e11-4b88-9c2a-1d6e0f4a2b10"
LISTAUS_UUID = "b4e7d1a6-8c33-4f02-a9d5-3e2c7b91f64a"

PARTY_ORDER = ["Kokoomus", "Sosiaalidemokraatit (SDP)", "Maalaisliitto",
               "Edistyspuolue", "Sitoutumaton"]
# Grammatical Finnish question per party (genitive / adjective forms).
PARTY_QUESTION = {
    "Kokoomus": "Luettele kaikki Kokoomuksen presidentit.",
    "Sosiaalidemokraatit (SDP)": "Luettele kaikki SDP:n presidentit.",
    "Maalaisliitto": "Luettele kaikki Maalaisliiton presidentit.",
    "Edistyspuolue": "Luettele kaikki Edistyspuolueen presidentit.",
    "Sitoutumaton": "Luettele kaikki sitoutumattomat presidentit.",
}

RECITE_FRONT = '<div class="ask">Luettele Suomen presidentit järjestyksessä (1.–13.).</div>'


def guid_for(text: str) -> str:
    """Deterministic 11-char guid from text (stable across rebuilds)."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()[:8]
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def build_party_rosters(rows):
    """rows = [(ordinal, name, canon_party), ...]. Returns [(front, back), ...]."""
    by_party = {}
    for ordn, name, party in rows:
        by_party.setdefault(party, []).append((ordn, name))
    out = []
    for party in PARTY_ORDER:
        members = sorted(by_party.get(party, []))
        ans = ", ".join(f"{name} ({ordn}.)" for ordn, name in members)
        out.append((PARTY_QUESTION[party], ans))
    return out


def build_recite_note(rows):
    """Returns (front, back). Each president is a native <details> revealed on tap
    — no JS, so it works the same across Anki desktop / AnkiDroid / AnkiMobile."""
    lis = "\n".join(f'<li><details><summary>näytä</summary>{name}</details></li>'
                    for _, name, _ in sorted(rows))
    back = ('<div class="hint">Napauta jokainen rivi vuorollaan.</div>\n'
            f'<ol id="reciteList">\n{lis}\n</ol>')
    return RECITE_FRONT, back


def build_trivia_notes():
    """Returns the TRIVIA list as [(front, back), ...]."""
    return list(TRIVIA)


def _basic_model(uuid: str, name: str, original_id: int) -> dict:
    """A minimal Front/Back note model used by the aggregate (koonti) notes."""
    def field(fname, ordn, fid):
        return {"name": fname, "ord": ordn, "id": fid, "font": "Arial", "size": 20,
                "rtl": False, "sticky": False, "collapsed": False, "description": "",
                "excludeFromSearch": False, "plainText": False,
                "preventDeletion": False, "tag": None}
    return {
        "__type__": "NoteModel",
        "crowdanki_uuid": uuid,
        "css": PRES_CSS,
        "flds": [field("Front", 0, original_id + 1), field("Back", 1, original_id + 2)],
        "tmpls": [{
            "name": name, "ord": 0, "id": original_id + 3,
            "qfmt": "{{Front}}",
            "afmt": "{{FrontSide}}\n<hr id=answer>\n{{Back}}",
            "bqfmt": "", "bafmt": "", "bfont": "", "bsize": 0, "did": None,
        }],
        "req": [[0, "all", [0]]],
        "sortf": 0, "type": 0,
        "latexPre": "", "latexPost": "", "latexsvg": False,
        "name": name, "originalId": original_id, "originalStockKind": 1,
    }


def _president_rows_for_test():
    """Test helper: source notes -> [(ordinal:int, name:str, canon_party:str)]."""
    deck = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for n in deck["notes"]:
        f = n["fields"]
        rows.append((int(_strip_tags(f[0]).rstrip(".")),
                     _strip_tags(f[1]), canon_party(_strip_tags(f[4]))))
    return rows


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _note(model_uuid: str, fields, guid_seed: str) -> dict:
    return {
        "__type__": "Note",
        "fields": fields,
        "guid": guid_for(guid_seed),
        "note_model_uuid": model_uuid,
        "tags": ["koonti"],
    }


def main() -> None:
    deck = json.loads(SRC.read_text(encoding="utf-8"))
    pres_model = deck["note_models"][0]

    # Capture (ordinal, clean name, canon party) BEFORE mutating the notes.
    rows, party_rows = [], []
    for n in deck["notes"]:
        ordn = int(_strip_tags(n["fields"][0]).rstrip("."))
        name = _strip_tags(n["fields"][1])
        rows.append((ordn, name))
        party_rows.append((ordn, name, canon_party(_strip_tags(n["fields"][4]))))
    pred, succ = compute_neighbors(rows)

    # Transform each per-president note in place + append enrichment fields.
    for n in deck["notes"]:
        f = n["fields"]
        ordn = int(_strip_tags(f[0]).rstrip("."))
        f[1] = _strip_tags(f[1])               # Name (strip Mannerheim's link)
        f[2] = normalize_years(f[2])           # Years
        f[4] = canon_party(_strip_tags(f[4]))  # Party
        f[5] = normalize_info(f[5])            # Info
        e = ENRICH[ordn]
        f.extend([e["Life"], e["Profession"], e["Birthplace"], e["KnownFor"],
                  e["Nickname"], e["Link"], pred[ordn], succ[ordn]])

    # Expand the per-president model.
    deck["note_models"][0] = build_president_model(pres_model)

    # Aggregate models + notes (A rosters -> B recite -> C trivia), all tagged koonti.
    deck["note_models"].extend([
        _basic_model(KOONTI_UUID, "Presidentit – Koonti", 700000000),
        _basic_model(LISTAUS_UUID, "Presidentit – Listaus", 710000000),
    ])
    for front, back in build_party_rosters(party_rows):
        deck["notes"].append(_note(KOONTI_UUID, [front, back], "roster:" + front))
    rfront, rback = build_recite_note(party_rows)
    deck["notes"].append(_note(LISTAUS_UUID, [rfront, rback], "recite:presidentit"))
    for front, back in build_trivia_notes():
        deck["notes"].append(_note(KOONTI_UUID, [front, back], "trivia:" + front))

    OUT.write_text(
        json.dumps(deck, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    koonti = sum(1 for n in deck["notes"] if "koonti" in n.get("tags", []))
    print(f"notes: {len(deck['notes'])} (13 presidents + {koonti} koonti)")
    print("templates:", [t["name"] for t in deck["note_models"][0]["tmpls"]])


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    main()
