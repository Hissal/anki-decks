# Suomen Presidentit Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regenerate `misc_decks/Suomen_presidentit/deck.json` from a source via a new idempotent builder that normalizes scraped HTML, adds 7 enrichment fields + 14 difficulty-ordered per-president cards, and generates aggregate "koonti" cards (party rosters, a JS tap-reveal recite card, trivia).

**Architecture:** A standalone `build_suomen_presidentit.py` reads the bootstrapped `deck.source.json`, transforms each note (normalize `Years`/`Info`/`Party`, merge enrichment from a separate data module, compute predecessor/successor), expands the per-president note model (fields + templates + `req` + CSS), appends two aggregate note models with generated notes, and writes `deck.json` with `ensure_ascii=False, indent=2, sort_keys=True`. Pure parsing helpers are unit-tested with pytest; the whole deck is checked by `validate_suomen_presidentit.py`.

**Tech Stack:** Python 3 (stdlib only at runtime — `json`, `re`, `html`, `hashlib`, `base64`, `copy`, `pathlib`), `pytest` for tests (dev-only). No new media. Reference pattern: `misc_decks/build_finland_subdivisions.py`.

**Testing note (repo-adapted):** This repo uses plain runnable scripts + `validate_*.py`, not a pytest suite. Per the user's simplicity preference, we apply test-first (pytest) only to the pure parsing helpers (Tasks 3–6) where regressions are easy and silent; model/aggregate/orchestration is verified by the integration build + `validate_suomen_presidentit.py` (Tasks 7–10). Run tests with `python -m pytest`.

**Paths (all absolute under the repo root `misc_decks/`):**
- Create: `misc_decks/build_suomen_presidentit.py`
- Create: `misc_decks/suomen_presidentit_data.py` (enrichment + trivia data tables)
- Create: `misc_decks/test_suomen_presidentit.py` (pytest)
- Create: `misc_decks/validate_suomen_presidentit.py`
- Create: `misc_decks/Suomen_presidentit/deck.source.json` (bootstrap copy of current `deck.json`)
- Modify (regenerated): `misc_decks/Suomen_presidentit/deck.json`

---

## Task 1: Branch + bootstrap source + tooling

**Files:**
- Create: `misc_decks/Suomen_presidentit/deck.source.json` (copy of current `deck.json`)

- [ ] **Step 1: Create the feature branch**

Run:
```bash
git checkout -b feat/suomen-presidentit-expansion
```
Expected: `Switched to a new branch 'feat/suomen-presidentit-expansion'`

- [ ] **Step 2: Bootstrap the untouched source**

Run (PowerShell):
```powershell
Copy-Item "misc_decks/Suomen_presidentit/deck.json" "misc_decks/Suomen_presidentit/deck.source.json"
```
Expected: `deck.source.json` exists and is byte-identical to `deck.json`.

- [ ] **Step 3: Confirm pytest is available**

Run:
```bash
python -m pytest --version
```
Expected: prints a pytest version. If missing: `pip install pytest`.

- [ ] **Step 4: Commit**

```bash
git add misc_decks/Suomen_presidentit/deck.source.json
git commit -m "chore(presidentit): bootstrap deck.source.json from upstream import"
```

---

## Task 2: Enrichment + trivia data module (research + USER REVIEW GATE)

**Files:**
- Create: `misc_decks/suomen_presidentit_data.py`

This task gathers the Finnish biographical facts. The values are researched from
**fi.wikipedia.org** (the per-president articles linked from
`https://fi.wikipedia.org/wiki/Luettelo_Suomen_presidenteistä`) and **must be
presented to the user as a table for sign-off before Step 3 commits them.**

`ENRICH` is keyed by the integer ordinal (1–13). Each value is a dict with keys
`Life`, `Profession`, `Birthplace`, `KnownFor`, `Nickname` (empty string when no
well-attested nickname exists). All text in **Finnish**, no HTML.

- [ ] **Step 1: Research all 13 presidents and assemble the table**

Use WebFetch on each president's fi.wikipedia article. Fill every field per the
format rules in the design spec §4. Worked example (ordinal 6 — use real values
of this exact shape for all rows):

```python
6: {
    "Life": "1867–1951",
    "Profession": "sotilas, Suomen marsalkka",
    "Birthplace": "Askainen",
    "KnownFor": "Ylipäällikkö toisessa maailmansodassa; valittiin presidentiksi poikkeuslailla 1944.",
    "Nickname": "Marski",
},
```

- [ ] **Step 2: Present the full 13-row table to the user and get approval**

Render a markdown table (Ordinal · Name · Life · Profession · Birthplace ·
KnownFor · Nickname) in chat. Wait for explicit "approved" / requested edits.
Do not proceed until approved.

- [ ] **Step 3: Write `suomen_presidentit_data.py` with the approved data**

```python
# -*- coding: utf-8 -*-
"""Curated Finnish facts for the Suomen Presidentit deck builder.

Researched from fi.wikipedia; reviewed/approved by the user. Keyed by ordinal
(1-13). Nickname is "" when no well-attested nickname exists.
"""

ENRICH = {
    1: {"Life": "...", "Profession": "...", "Birthplace": "...", "KnownFor": "...", "Nickname": "..."},
    # ... 2..13, every field filled from the approved table ...
}

# Canonical party display names (also used to group the rosters).
PARTY_CANON = {
    "Edistyspuolue": "Edistyspuolue",
    "Maalaisliitto": "Maalaisliitto",
    "Kokoomuspuolue": "Kokoomus",
    "Kokoomus": "Kokoomus",
    "Sosiaalidemokraatti": "Sosiaalidemokraatit (SDP)",
    "Sitoutumaton": "Sitoutumaton",
}

# Aggregate trivia (deck §6 C). (question, answer) — Finnish, no HTML.
TRIVIA = [
    ("Kuka oli Suomen ensimmäinen presidentti?", "K. J. Ståhlberg (1.)"),
    ("Kuka oli Suomen ensimmäinen naispresidentti?", "Tarja Halonen (11.)"),
    ("Kuka istui presidenttinä pisimpään?", "Urho Kekkonen (8.), n. 26 vuotta"),
    ("Kuka on Suomen nykyinen presidentti?", "Alexander Stubb (13.)"),
    ("Kuka presidentti kuoli virassa?", "Kyösti Kallio (4.)"),
    ("Ketkä presidentit erosivat kesken kauden?", "Ryti (5.), Mannerheim (6.), Kekkonen (8.)"),
    ("Ketkä valittiin tai joiden kautta jatkettiin poikkeuslailla?", "Mannerheim (6.) ja Kekkonen (8.)"),
    ("Ketkä olivat presidentteinä toisen maailmansodan aikana?", "Kallio (4.), Ryti (5.), Mannerheim (6.)"),
    ("Kuka oli presidentti, kun Suomi liittyi EU:hun (1995)?", "Martti Ahtisaari (10.)"),
    ("Kuka oli presidentti, kun Suomi liittyi Natoon (2023)?", "Sauli Niinistö (12.)"),
]
```

- [ ] **Step 4: Commit**

```bash
git add misc_decks/suomen_presidentit_data.py
git commit -m "feat(presidentit): add approved Finnish enrichment + trivia data"
```

---

## Task 3: `normalize_years` (TDD)

**Files:**
- Create: `misc_decks/build_suomen_presidentit.py` (start the module)
- Test: `misc_decks/test_suomen_presidentit.py`

- [ ] **Step 1: Write the failing test**

Create `misc_decks/test_suomen_presidentit.py`:
```python
# -*- coding: utf-8 -*-
import build_suomen_presidentit as b


def test_normalize_years_plain_range():
    raw = "25.7. 1919 - 2.3.1 1925"
    assert b.normalize_years(raw) == "1919–1925"


def test_normalize_years_strips_wikipedia_links():
    raw = ('<a href="https://fi.wikipedia.org/wiki/2._maaliskuuta">2.3.</a>'
           '<a href="https://fi.wikipedia.org/wiki/1925">1925</a>&nbsp;–&nbsp;'
           '<a href="https://fi.wikipedia.org/wiki/1931">1931</a>')
    assert b.normalize_years(raw) == "1925–1931"


def test_normalize_years_died_in_office_marker():
    raw = ('<a href="x">1.3.</a><a href="y">1937</a>&nbsp;–&nbsp;'
           '<a href="z">19.12.</a><a href="w">1940</a>†')
    assert b.normalize_years(raw) == "1937–1940 †"


def test_normalize_years_current_term():
    assert b.normalize_years("1.3.2024 -&gt;") == "2024–"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest misc_decks/test_suomen_presidentit.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'build_suomen_presidentit'` (run from `misc_decks/`) or `AttributeError: normalize_years`.

Note: run pytest from inside `misc_decks/` so the bare imports resolve:
```bash
cd misc_decks && python -m pytest test_suomen_presidentit.py -q
```

- [ ] **Step 3: Write minimal implementation**

Create `misc_decks/build_suomen_presidentit.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the expanded "Suomen Presidentit" deck from deck.source.json.

Idempotent: always starts from deck.source.json. Normalizes scraped HTML, merges
curated Finnish enrichment (suomen_presidentit_data.ENRICH), computes
predecessor/successor, installs 14 per-president templates + two aggregate note
types (party rosters, JS recite card, trivia), and writes deck.json.
"""

import base64
import copy
import hashlib
import html as html_mod
import json
import re
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "Suomen_presidentit"
SRC = OUT_DIR / "deck.source.json"
OUT = OUT_DIR / "deck.json"

_TAG_RE = re.compile(r"<[^>]+>")
_YEAR_RE = re.compile(r"(\d{4})")


def _strip_tags(s: str) -> str:
    """Remove HTML tags and decode entities to plain text."""
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd misc_decks && python -m pytest test_suomen_presidentit.py -q
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add misc_decks/build_suomen_presidentit.py misc_decks/test_suomen_presidentit.py
git commit -m "feat(presidentit): normalize_years helper + tests"
```

---

## Task 4: `normalize_info` and `canon_party` (TDD)

**Files:**
- Modify: `misc_decks/build_suomen_presidentit.py`
- Test: `misc_decks/test_suomen_presidentit.py`

- [ ] **Step 1: Add failing tests**

Append to `misc_decks/test_suomen_presidentit.py`:
```python
def test_normalize_info_strips_table_wrapper():
    raw = "<table><tbody><tr><td><br>Ståhlbergin kausi alkoi myöhemmin.</td></tr></tbody></table>"
    assert b.normalize_info(raw) == "Ståhlbergin kausi alkoi myöhemmin."


def test_normalize_info_strips_citation_sup():
    raw = ('Koiviston kaudella valtaa vähennettiin.'
           '<sup><a href="x">[4]</a></sup>&nbsp;Päätös ei koskenut häntä.')
    assert b.normalize_info(raw) == "Koiviston kaudella valtaa vähennettiin. Päätös ei koskenut häntä."


def test_canon_party_maps_variants():
    assert b.canon_party("Kokoomuspuolue") == "Kokoomus"
    assert b.canon_party("Kokoomus") == "Kokoomus"
    assert b.canon_party("Sosiaalidemokraatti") == "Sosiaalidemokraatit (SDP)"
    assert b.canon_party("Sitoutumaton") == "Sitoutumaton"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: FAIL — `AttributeError: normalize_info` / `canon_party`.

- [ ] **Step 3: Implement**

Add to `misc_decks/build_suomen_presidentit.py` (import the data table near the top, after the stdlib imports):
```python
from suomen_presidentit_data import ENRICH, PARTY_CANON, TRIVIA
```
And add the functions:
```python
def normalize_info(raw: str) -> str:
    """Strip <sup> citations + <table> wrappers, collapse whitespace, keep prose."""
    without_sup = re.sub(r"<sup>.*?</sup>", "", raw, flags=re.DOTALL)
    text = _strip_tags(without_sup)
    return re.sub(r"\s+", " ", text).strip()


def canon_party(raw: str) -> str:
    """Map a scraped party string to its canonical display name."""
    return PARTY_CANON.get(raw.strip(), raw.strip())
```

- [ ] **Step 4: Run to verify pass**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add misc_decks/build_suomen_presidentit.py misc_decks/test_suomen_presidentit.py
git commit -m "feat(presidentit): normalize_info + canon_party helpers + tests"
```

---

## Task 5: `compute_neighbors` (TDD)

**Files:**
- Modify: `misc_decks/build_suomen_presidentit.py`
- Test: `misc_decks/test_suomen_presidentit.py`

- [ ] **Step 1: Add failing test**

Append to the test file:
```python
def test_compute_neighbors():
    rows = [(1, "K. J. Ståhlberg"), (2, "Lauri Kristian Relander"), (3, "P.E. Svinhufvud")]
    pred, succ = b.compute_neighbors(rows)
    assert pred[1] == ""                       # first has no predecessor
    assert succ[1] == "Lauri Kristian Relander (2.)"
    assert pred[2] == "K. J. Ståhlberg (1.)"
    assert succ[3] == ""                        # last has no successor
```

- [ ] **Step 2: Run to verify failure**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: FAIL — `AttributeError: compute_neighbors`.

- [ ] **Step 3: Implement**

Add to the builder:
```python
def compute_neighbors(rows):
    """rows = [(ordinal:int, name:str), ...] sorted by ordinal.

    Returns (pred, succ) dicts keyed by ordinal; value is 'Name (N.)' or ''.
    """
    rows = sorted(rows)
    pred, succ = {}, {}
    for i, (ordn, name) in enumerate(rows):
        pred[ordn] = f"{rows[i-1][1]} ({rows[i-1][0]}.)" if i > 0 else ""
        succ[ordn] = f"{rows[i+1][1]} ({rows[i+1][0]}.)" if i < len(rows) - 1 else ""
    return pred, succ
```

- [ ] **Step 4: Run to verify pass**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add misc_decks/build_suomen_presidentit.py misc_decks/test_suomen_presidentit.py
git commit -m "feat(presidentit): compute_neighbors helper + tests"
```

---

## Task 6: Per-president note model (fields + 14 templates + req + CSS)

**Files:**
- Modify: `misc_decks/build_suomen_presidentit.py`
- Test: `misc_decks/test_suomen_presidentit.py`

The new fields and templates are data-driven from two tables so the 14 cards stay
DRY. Card front = a labeled prompt; back = a shared profile for every card.

- [ ] **Step 1: Add failing test**

Append to the test file:
```python
def test_president_template_order_and_req():
    model = b.build_president_model()
    names = [t["name"] for t in model["tmpls"]]
    assert names == [
        "Image → Name", "KnownFor → Name", "Nickname → Name", "Years → Name",
        "Ordinal → Name", "Name → Ordinal", "Name → Party", "Name → KnownFor",
        "Name → Profession", "Name → Birthplace", "Name → Predecessor",
        "Name → Successor", "Name → Years", "Name → Life",
    ]
    # ord is sequential
    assert [t["ord"] for t in model["tmpls"]] == list(range(14))
    # req is ord-indexed and matches the card count
    assert [r[0] for r in model["req"]] == list(range(14))
    # field names include existing + new, existing first 6 preserved in order
    fnames = [f["name"] for f in model["flds"]]
    assert fnames[:6] == ["Ordinal", "Name", "Years", "Image", "Party", "Info"]
    assert set(fnames[6:]) == {"Life", "Profession", "Birthplace", "KnownFor",
                               "Nickname", "Predecessor", "Successor"}


def test_president_req_field_indexes():
    model = b.build_president_model()
    idx = {f["name"]: i for i, f in enumerate(model["flds"])}
    req_by_name = {model["tmpls"][r[0]]["name"]: (r[1], r[2]) for r in model["req"]}
    assert req_by_name["Image → Name"] == ("any", [idx["Image"]])
    assert req_by_name["Name → Party"] == ("all", [idx["Party"]])
    assert req_by_name["Name → Successor"] == ("all", [idx["Successor"]])
```

- [ ] **Step 2: Run to verify failure**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: FAIL — `AttributeError: build_president_model`.

- [ ] **Step 3: Implement**

Add to the builder. Field ids/template ids are fixed constants so the model is
stable across rebuilds (idempotent). `PRES_MODEL_UUID` is the existing model's
uuid, read from source at runtime in `main()`; `build_president_model()` takes the
source model so existing field ids/uuid survive.

```python
NEW_FIELDS = ["Life", "Profession", "Birthplace", "KnownFor", "Nickname",
              "Predecessor", "Successor"]
_NEW_FIELD_ID_BASE = 800000000  # arbitrary stable ids for the appended fields

# (template name, front HTML, req-kind, req-field-name)
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

# Shared profile back for every card.
PROFILE_BACK = """{{FrontSide}}
<hr id=answer>
<div class="name">{{Name}}</div>
{{#Image}}<div class="pic">{{Image}}</div>{{/Image}}
<table class="profile">
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
</table>
{{#Info}}<div class="info">{{Info}}</div>{{/Info}}"""

PRES_CSS = """.card { font-family: arial; font-size: 20px; line-height: 1.5;
  text-align: center; color: black; background-color: white; }
.ask { color: #555; font-size: 16px; margin-top: .6em; }
.clue { font-size: 24px; }
.name { font-size: 26px; font-weight: bold; margin-bottom: .3em; }
.pic img { max-height: 200px; }
table.profile { margin: .6em auto; border-collapse: collapse; text-align: left; }
table.profile th { color: #777; font-weight: normal; padding: 2px 10px 2px 0;
  vertical-align: top; white-space: nowrap; }
table.profile td { padding: 2px 0; }
.info { font-size: 15px; color: #444; margin-top: .6em; max-width: 36em;
  margin-left: auto; margin-right: auto; text-align: left; }"""


def build_president_model(src_model: dict) -> dict:
    """Return the expanded per-president note model (fields, 14 templates, req, css)."""
    model = copy.deepcopy(src_model)

    # Append the new fields after the existing 6, preserving their ord.
    existing = model["flds"]
    base_ord = len(existing)
    proto_field = copy.deepcopy(existing[0])
    for i, fname in enumerate(NEW_FIELDS):
        f = copy.deepcopy(proto_field)
        f["name"] = fname
        f["ord"] = base_ord + i
        f["id"] = _NEW_FIELD_ID_BASE + i
        existing.append(f)

    idx = {f["name"]: f["ord"] for f in existing}

    proto_tmpl = copy.deepcopy(model["tmpls"][0])
    tmpls, req = [], []
    for ordn, (name, front, kind, field) in enumerate(CARDS):
        t = copy.deepcopy(proto_tmpl)
        t["name"] = name
        t["ord"] = ordn
        t["id"] = 900000000 + ordn
        t["qfmt"] = front
        t["afmt"] = PROFILE_BACK
        t["bqfmt"] = ""
        t["bafmt"] = ""
        tmpls.append(t)
        req.append([ordn, kind, [idx[field]]])

    model["tmpls"] = tmpls
    model["req"] = req
    model["css"] = PRES_CSS
    model["sortf"] = idx["Name"]
    return model
```

- [ ] **Step 4: Run to verify pass**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: 10 passed.

Note: `test_president_template_order_and_req` and `test_president_req_field_indexes`
call `b.build_president_model()` with no args, but the implementation takes
`src_model`. Fix the tests to load the source model first:
```python
import json, pathlib
def _src_president_model():
    deck = json.loads((pathlib.Path(__file__).resolve().parent
                       / "Suomen_presidentit" / "deck.source.json").read_text(encoding="utf-8"))
    return deck["note_models"][0]
```
and call `b.build_president_model(_src_president_model())` in both tests. (Add this
helper at the top of the test file.) Re-run to confirm 10 passed.

- [ ] **Step 5: Commit**

```bash
git add misc_decks/build_suomen_presidentit.py misc_decks/test_suomen_presidentit.py
git commit -m "feat(presidentit): expanded per-president model (14 cards, req, profile back)"
```

---

## Task 7: Aggregate note models + generated notes (rosters, recite, trivia)

**Files:**
- Modify: `misc_decks/build_suomen_presidentit.py`
- Test: `misc_decks/test_suomen_presidentit.py`

- [ ] **Step 1: Add failing tests**

Append to the test file:
```python
def test_party_rosters_partition_all_13():
    notes = b._president_rows_for_test()  # [(ordinal, name, canon_party), ...] len 13
    rosters = b.build_party_rosters(notes)
    # 5 parties, every president appears exactly once across the answers
    assert len(rosters) == 5
    counts = {"Kokoomus": 4, "Sosiaalidemokraatit (SDP)": 3, "Maalaisliitto": 3,
              "Edistyspuolue": 2, "Sitoutumaton": 1}
    got = {front.split(" presidentit")[0].split("Luettele kaikki ")[1]: ans
           for front, ans in rosters}
    for party, n in counts.items():
        assert got[party].count("(") == n


def test_recite_note_lists_all_13():
    notes = b._president_rows_for_test()
    front, back = b.build_recite_note(notes)
    assert "järjestyksessä" in front
    for _, name, _ in notes:
        assert name in back
    assert "<script>" in back  # JS reveal present


def test_trivia_count_matches_data():
    assert len(b.build_trivia_notes()) == len(b.TRIVIA)


def test_guid_for_is_deterministic():
    assert b.guid_for("abc") == b.guid_for("abc")
    assert b.guid_for("abc") != b.guid_for("abd")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: FAIL — missing `_president_rows_for_test` / `build_party_rosters` / etc.

- [ ] **Step 3: Implement**

Add to the builder. The two aggregate models are minimal Basic-style note types;
the recite card carries the incremental-reveal JS.

```python
KOONTI_UUID = "7f3a9c20-5e11-4b88-9c2a-1d6e0f4a2b10"
LISTAUS_UUID = "b4e7d1a6-8c33-4f02-a9d5-3e2c7b91f64a"

PARTY_ORDER = ["Kokoomus", "Sosiaalidemokraatit (SDP)", "Maalaisliitto",
               "Edistyspuolue", "Sitoutumaton"]

RECITE_FRONT = '<div class="ask">Luettele Suomen presidentit järjestyksessä (1→13).</div>'
RECITE_JS = """
<script>(function(){
  var items = document.querySelectorAll('#reciteList .r');
  var i = 0;
  function reveal(){ if (i < items.length){ items[i].style.visibility = 'visible'; i++; } }
  document.addEventListener('click', reveal);
  document.addEventListener('keydown', function(e){
    if (e.code === 'Space' || e.key === ' ') { e.preventDefault(); reveal(); }
  });
})();</script>"""


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
        out.append((f"Luettele kaikki {party} presidentit.", ans))
    return out


def build_recite_note(rows):
    """Returns (front, back-with-JS). Back lists all names, hidden until tapped."""
    lis = "\n".join(
        f'<li><span class="r">{name}</span></li>'
        for _, name, _ in sorted(rows))
    back = (RECITE_FRONT + '\n<hr id=answer>\n'
            '<div class="hint">Napauta / välilyönti paljastaa seuraavan.</div>\n'
            f'<ol id="reciteList">\n{lis}\n</ol>\n' + RECITE_JS)
    return RECITE_FRONT, back


def build_trivia_notes():
    """Returns the TRIVIA list as [(front, back), ...]."""
    return list(TRIVIA)


def _president_rows_for_test():
    """Test helper: load source notes -> [(ordinal:int, name:str, canon_party:str)]."""
    deck = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for n in deck["notes"]:
        f = n["fields"]
        ordn = int(_strip_tags(f[0]).rstrip("."))
        rows.append((ordn, _strip_tags(f[1]), canon_party(_strip_tags(f[4]))))
    return rows


def _basic_model(uuid, name, with_js):
    """A minimal Front/Back note model used by the aggregate notes."""
    afmt = "{{FrontSide}}\n<hr id=answer>\n{{Back}}"
    return {
        "__type__": "NoteModel",
        "crowdanki_uuid": uuid,
        "css": PRES_CSS,
        "flds": [
            {"name": "Front", "ord": 0, "id": 700000001, "font": "Arial", "size": 20,
             "rtl": False, "sticky": False, "collapsed": False, "description": "",
             "excludeFromSearch": False, "plainText": False, "preventDeletion": False, "tag": None},
            {"name": "Back", "ord": 1, "id": 700000002, "font": "Arial", "size": 20,
             "rtl": False, "sticky": False, "collapsed": False, "description": "",
             "excludeFromSearch": False, "plainText": False, "preventDeletion": False, "tag": None},
        ],
        "tmpls": [{"name": name, "ord": 0, "id": 710000001, "qfmt": "{{Front}}",
                   "afmt": afmt, "bqfmt": "", "bafmt": "", "bfont": "", "bsize": 0, "did": None}],
        "req": [[0, "all", [0]]],
        "sortf": 0, "type": 0, "latexPre": "", "latexPost": "", "latexsvg": False,
        "name": name, "originalStockKind": 1,
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add misc_decks/build_suomen_presidentit.py misc_decks/test_suomen_presidentit.py
git commit -m "feat(presidentit): aggregate rosters/recite/trivia builders + tests"
```

---

## Task 8: `main()` orchestration + first real build

**Files:**
- Modify: `misc_decks/build_suomen_presidentit.py`

- [ ] **Step 1: Implement `main()`**

Add to the builder:
```python
def _note(model_uuid, fields, guid_seed):
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
    pres_uuid = pres_model["crowdanki_uuid"]

    # Order rows by ordinal for neighbor computation.
    rows = []
    for n in deck["notes"]:
        ordn = int(_strip_tags(n["fields"][0]).rstrip("."))
        rows.append((ordn, _strip_tags(n["fields"][1])))
    pred, succ = compute_neighbors(rows)

    # Transform each per-president note in place.
    for n in deck["notes"]:
        f = n["fields"]
        ordn = int(_strip_tags(f[0]).rstrip("."))
        f[2] = normalize_years(f[2])          # Years
        f[4] = canon_party(_strip_tags(f[4]))  # Party
        f[5] = normalize_info(f[5])            # Info
        e = ENRICH[ordn]
        f.extend([e["Life"], e["Profession"], e["Birthplace"], e["KnownFor"],
                  e["Nickname"], pred[ordn], succ[ordn]])

    # Expand the per-president model.
    deck["note_models"][0] = build_president_model(pres_model)

    # Aggregate models.
    koonti = _basic_model(KOONTI_UUID, "Presidentit – Koonti", with_js=False)
    listaus = _basic_model(LISTAUS_UUID, "Presidentit – Listaus", with_js=True)
    deck["note_models"].extend([koonti, listaus])

    # Aggregate notes: rosters (A) -> recite (B) -> trivia (C).
    party_rows = [(o, name, canon_party(_strip_tags(orig_party)))
                  for (o, name), orig_party in
                  zip(rows, [_strip_tags(n["fields"][4]) for n in
                             json.loads(SRC.read_text(encoding="utf-8"))["notes"]])]
    for front, back in build_party_rosters(party_rows):
        deck["notes"].append(_note(KOONTI_UUID, [front, back], "roster:" + front))
    rfront, rback = build_recite_note(party_rows)
    deck["notes"].append(_note(LISTAUS_UUID, [rfront, rback], "recite:presidentit"))
    for front, back in build_trivia_notes():
        deck["notes"].append(_note(KOONTI_UUID, [front, back], "trivia:" + front))

    OUT.write_text(
        json.dumps(deck, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(f"notes: {len(deck['notes'])} "
          f"(13 presidents + {len(deck['notes']) - 13} koonti)")
    print("templates:", [t["name"] for t in deck["note_models"][0]["tmpls"]])


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    main()
```

Note: the `party_rows` construction above re-reads the source to recover the
*original* party strings (the in-place loop already canonicalized `f[4]`). Keep it
exactly as written.

- [ ] **Step 2: Run the build**

Run:
```bash
cd misc_decks && python build_suomen_presidentit.py
```
Expected output:
```
notes: 29 (13 presidents + 16 koonti)
templates: ['Image → Name', 'KnownFor → Name', ... 'Name → Life']
```
Koonti count = 5 rosters + 1 recite + `len(TRIVIA)` (10) = 16, so the printed
total is `13 + 16 = 29`. Confirm the number matches.

- [ ] **Step 3: Re-run to confirm idempotency**

Run:
```bash
cd misc_decks && python build_suomen_presidentit.py && git diff --stat misc_decks/Suomen_presidentit/deck.json
```
Run the build twice in a row; the second run must produce **no diff** versus the
first run's output (stable ids + deterministic guids). Expected: clean / identical.

- [ ] **Step 4: Commit**

```bash
git add misc_decks/build_suomen_presidentit.py misc_decks/Suomen_presidentit/deck.json
git commit -m "feat(presidentit): main() orchestration + regenerated deck.json"
```

---

## Task 9: `validate_suomen_presidentit.py` + verification

**Files:**
- Create: `misc_decks/validate_suomen_presidentit.py`

- [ ] **Step 1: Write the validator**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the generated Suomen Presidentit deck.json (design spec §11)."""

import json
import re
from pathlib import Path

DECK_DIR = Path(__file__).resolve().parent / "Suomen_presidentit"
DECK = DECK_DIR / "deck.json"
MEDIA = DECK_DIR / "media"
IMG_RE = re.compile(r'src="([^"]+)"')


def main() -> int:
    deck = json.loads(DECK.read_text(encoding="utf-8"))
    errors = []

    models = {m["crowdanki_uuid"]: m for m in deck["note_models"]}
    pres = deck["note_models"][0]

    # 14 templates, ord-indexed req of equal length.
    if len(pres["tmpls"]) != 14:
        errors.append(f"expected 14 president templates, got {len(pres['tmpls'])}")
    if [r[0] for r in pres["req"]] != list(range(len(pres["tmpls"]))):
        errors.append("president req is not ord-indexed 0..n")

    # Per-president notes intact (13, guids non-empty, all fields filled length).
    pres_notes = [n for n in deck["notes"] if n["note_model_uuid"] == pres["crowdanki_uuid"]]
    if len(pres_notes) != 13:
        errors.append(f"expected 13 president notes, got {len(pres_notes)}")
    nfields = len(pres["flds"])
    for n in pres_notes:
        if len(n["fields"]) != nfields:
            errors.append(f"note {n['guid']} has {len(n['fields'])} fields, model has {nfields}")
        if not n["guid"]:
            errors.append("empty guid on a president note")

    # Years normalized: no leftover HTML tags / nbsp.
    for n in pres_notes:
        yrs = n["fields"][2]
        if "<" in yrs or "&nbsp;" in yrs:
            errors.append(f"Years not normalized: {yrs!r}")

    # Every <img> resolves to a media file.
    for n in pres_notes:
        for m in IMG_RE.findall(n["fields"][3]):
            if not (MEDIA / m).exists():
                errors.append(f"missing media: {m}")

    # Aggregate notes present and tagged koonti.
    koonti = [n for n in deck["notes"] if "koonti" in n.get("tags", [])]
    if len(koonti) < 6:
        errors.append(f"expected >=6 koonti notes, got {len(koonti)}")

    # Guids unique across the whole deck.
    guids = [n["guid"] for n in deck["notes"]]
    if len(guids) != len(set(guids)):
        errors.append("duplicate guids in deck")

    # Party rosters partition the 13 presidents (count '(' across roster answers).
    roster_ans = [n["fields"][1] for n in koonti
                  if n["fields"][0].startswith("Luettele kaikki")]
    total = sum(a.count("(") for a in roster_ans)
    if total != 13:
        errors.append(f"party rosters cover {total} presidents, expected 13")

    if errors:
        print("FAIL:")
        for e in errors:
            print("  -", e)
        return 1
    print(f"OK: {len(pres_notes)} presidents, {len(koonti)} koonti notes, "
          f"{len(pres['tmpls'])} templates, rosters cover {total}.")
    return 0


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
```

- [ ] **Step 2: Run the validator**

Run:
```bash
cd misc_decks && python validate_suomen_presidentit.py
```
Expected: `OK: 13 presidents, 16 koonti notes, 14 templates, rosters cover 13.`

- [ ] **Step 3: Run the full test suite once more**

Run: `cd misc_decks && python -m pytest test_suomen_presidentit.py -q`
Expected: 14 passed.

- [ ] **Step 4: Commit**

```bash
git add misc_decks/validate_suomen_presidentit.py
git commit -m "feat(presidentit): deck validator (spec §11 invariants)"
```

---

## Task 10: Manual Anki verification + finish branch

**Files:** none (manual + handoff)

- [ ] **Step 1: Import into Anki and verify rendering**

In Anki: *File → Import* (or CrowdAnki import) the `Suomen_presidentit` folder.
Verify:
- A president card shows the labeled front (e.g. *"{name}" / Mikä puolue?*) and the
  profile back renders the table + image.
- Sparse cards are absent where expected (Ståhlberg has no *Edeltäjä?* card;
  Stubb has no *Seuraaja?* card; presidents without a nickname have no
  *Nickname → Name* card).
- **The recite card (Presidentit – Listaus):** on the answer side, each
  tap / Space reveals the next president name one at a time, 1→13.

- [ ] **Step 2: If the JS reveal misbehaves on the user's client**

Fallback already present (names are in the DOM; "reveal all" = keep tapping). If
taps don't register on the user's client, change the reveal trigger in `RECITE_JS`
to a button: add `<button onclick="reveal()">Seuraava</button>` inside the back and
expose `reveal` on `window`. Re-run the build + validator, re-import.

- [ ] **Step 3: Finish the branch**

Use the superpowers:finishing-a-development-branch skill to choose merge / PR /
cleanup. Summarize: new builder + data + validator + tests; regenerated deck.json
(13 presidents × up to 14 cards + 16 koonti notes).

---

## Self-Review (completed by plan author)

**Spec coverage:** §3 decisions → Tasks 1–9. §4 fields → Task 6 (`NEW_FIELDS`) +
Task 8 (enrich merge). §5 14 cards/order/req → Task 6 (`CARDS`). §6 A/B/C
aggregates → Task 7 + Task 8. §7 normalization → Tasks 3–4 + Task 8. §8 styling →
Task 6 (`PRES_CSS`, `PROFILE_BACK`). §9 builder mechanics → Task 8. §10 risks →
Task 8 Step 3 (idempotency) + Task 10 (JS verify). §11 verification → Task 9. §12
out-of-scope respected (no new media; stays CrowdAnki). Enrichment review gate →
Task 2 Step 2.

**Placeholder scan:** Task 2's `ENRICH`/`PARTY_CANON` values are filled by the
research step before commit (the only intentionally deferred content, gated by
user review). No `TODO`/`TBD` in code steps.

**Type consistency:** `build_president_model(src_model)` takes the source model
(Task 6 test helper aligned in Step 4 note). `_basic_model(..., with_js)` accepts
the flag (used in Task 8); JS lives in `RECITE_JS` and is injected by
`build_recite_note`, while `_basic_model` stays generic — `with_js` is currently
unused by `_basic_model` and exists for signature symmetry; the recite JS is in the
note's Back field, not the model, so this is intentional. `guid_for`,
`canon_party`, `normalize_years/info`, `compute_neighbors` names match across tasks.
