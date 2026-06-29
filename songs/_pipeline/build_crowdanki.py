#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a CrowdAnki `deck.json` for one song from its three Lines/Blocks TSVs.

The TSVs stay the source of truth; this is a *second* export format layered on
top so the deck can be imported in one click via the CrowdAnki add-on (no
manual collection.media copy, no per-note-type template paste).

What it emits into the song dir:
  - deck.json   re-importable CrowdAnki deck (deck named with the Chinese
                title; stable GUIDs so a re-import UPDATES notes, never dupes)
  - media/      already holds the per-line clips + block combos; this script
                also drops `_ruby.js` + `_song_ruby.js` in there so the import
                installs the template JS deps automatically.

Three note models, shared by EVERY song (so all song decks reference the same
note types in Anki, not one set per song):

  Chinese (song-line)         Basic  (type 0)  — Recall + Reading cards
  Chinese (song-line-cloze)   Cloze  (type 1)  — word-level cloze
  Chinese (song-block)        Cloze  (type 1)  — whole-line block cloze

Model UUIDs are derived from the model NAME (global, stable). Note GUIDs are
derived from the note role + its TSV Key (Basic and Cloze share a Key, so the
role disambiguates). Deck UUID is derived from the song slug.

The card templates + field lists below mirror songs/_note_types/*.md; the CSS
is read live from songs/_note_types/styling.css. If you edit a template in one
place, mirror it in the other.

Run:  python songs/_pipeline/build_crowdanki.py --song-dir songs/<slug>
Deps: standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import uuid
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PIPELINE_DIR = Path(__file__).resolve().parent
SONGS_DIR = PIPELINE_DIR.parent
NOTE_TYPES_DIR = SONGS_DIR / "_note_types"
CSS_PATH = NOTE_TYPES_DIR / "styling.css"
SONG_RUBY_JS = NOTE_TYPES_DIR / "_song_ruby.js"
RUBY_JS = SONGS_DIR.parent / "note_type" / "Chinese_anki_decks" / "_ruby.js"

# Fixed namespace so uuid5() is reproducible across runs / machines.
NS = uuid.UUID("a1b2c3d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d")

_BASE91 = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "!#$%&()*+,-./:;<=>?@[]^_`{|}~"
)

DEFAULT_DECK_PARENT = "Chinese::Songs"

# --------------------------------------------------------------------------
# Card templates (mirror songs/_note_types/*.md). { } that belong to Anki/JS
# are literal here — these are plain strings, NOT f-strings.
# --------------------------------------------------------------------------

LINE_RECALL_Q = """\
{{#PrevHanzi}}
<div class="meta">{{SongSlug}} · what's the next line?</div>

<div class="audio">{{PrevAudio}}</div>

<div class="hanzi-block prev">{{PrevHanzi}}</div>

<div class="prompt">→ what comes next?</div>
{{/PrevHanzi}}

{{^PrevHanzi}}
<div class="meta">{{SongSlug}} · first line</div>

<div class="prompt">→ how does the song start?</div>
{{/PrevHanzi}}"""

LINE_RECALL_A = """\
<div class="meta">{{SongSlug}} · line {{LineNo}}</div>

{{#PrevHanzi}}
<div class="hanzi-block prev">{{PrevHanzi}}</div>
<hr>
{{/PrevHanzi}}

<div class="audio">{{Audio}}</div>

<div class="hanzi-block show-all-ruby"
     id="songline-recall-hanzi"
     data-hanzi="{{text:HanziPlain}}"
     data-pinyin="{{text:Pinyin}}"></div>

<div class="english">{{English}}</div>

<script src="_ruby.js"></script>
<script>
  window.ankiDecks.mountRuby("songline-recall-hanzi", { revealed: true });
</script>"""

LINE_READING_Q = """\
<div class="meta">{{SongSlug}} · line {{LineNo}}</div>

<div class="audio">{{Audio}}</div>

<div class="hanzi-block"
     id="songline-hanzi"
     data-hanzi="{{text:HanziPlain}}"
     data-pinyin="{{text:Pinyin}}"></div>

<button class="toggle-btn" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

<script src="_ruby.js"></script>
<script>
  window.ankiDecks.mountRuby("songline-hanzi", { revealed: false });
  window.ankiDecks.attachToggle("songline-hanzi", "toggle-pinyin-btn");
</script>"""

LINE_READING_A = """\
<div class="meta">{{SongSlug}} · line {{LineNo}}</div>

<div class="audio">{{Audio}}</div>

<div class="hanzi-block show-all-ruby"
     id="songline-hanzi-back"
     data-hanzi="{{text:HanziPlain}}"
     data-pinyin="{{text:Pinyin}}"></div>

<hr>

<div class="english">{{English}}</div>
<div class="breakdown">{{Breakdown}}</div>

<script src="_ruby.js"></script>
<script>
  window.ankiDecks.mountRuby("songline-hanzi-back", { revealed: true });
</script>"""

CLOZE_Q = """\
<div class="meta">{{SongSlug}} · line {{LineNo}} · cloze</div>

<div class="hanzi-block">{{cloze:Hanzi}}</div>"""

CLOZE_A = """\
<div class="meta">{{SongSlug}} · line {{LineNo}} · cloze</div>

<div class="audio">{{Audio}}</div>

<div class="hanzi-block show-all-ruby"
     id="songcloze-back-hanzi"
     data-pinyin="{{text:Pinyin}}">{{cloze:Hanzi}}</div>

<hr>

<div class="english">{{English}}</div>
<div class="breakdown">{{Breakdown}}</div>

<script src="_ruby.js"></script>
<script src="_song_ruby.js"></script>
<script>
  window.songsRuby.mountElement("songcloze-back-hanzi");
</script>"""

BLOCK_Q = """\
<div class="meta">{{SongSlug}} · block {{BlockNo}}</div>

<div class="audio-mount" id="songblock-audio"></div>

<div class="lines-block"
     id="songblock-lines"
     data-pinyin="{{text:Pinyin}}">{{cloze:Lines}}</div>

<button class="toggle-btn" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

<script src="_ruby.js"></script>
<script src="_song_ruby.js"></script>
<script>
  window.songsRuby.playBlockAudio("songblock-lines", "songblock-audio", "{{SongSlug}}", "{{BlockNo}}");
  window.songsRuby.mountLines("songblock-lines");
  window.ankiDecks.attachToggle("songblock-lines", "toggle-pinyin-btn");
</script>"""

BLOCK_A = """\
<div class="meta">{{SongSlug}} · block {{BlockNo}}</div>

<div class="audio-mount" data-soundfile="{{soundfile:BlockAudio}}"></div>

<div class="lines-block show-all-ruby"
     id="songblock-lines-back"
     data-pinyin="{{text:Pinyin}}">{{cloze:Lines}}</div>

<hr>

<div class="english">{{English}}</div>
<div class="breakdown">{{Breakdown}}</div>

<script src="_ruby.js"></script>
<script src="_song_ruby.js"></script>
<script>
  window.ankiDecks.mountAutoplayAudio(".audio-mount", { controls: true });
  window.songsRuby.mountLines("songblock-lines-back");
</script>"""


# --------------------------------------------------------------------------
# Model definitions. `tsv` is the suffix of the song's TSV file; `cloze_ord`
# is the field ordinal Anki clozes on (None for the Basic model).
# --------------------------------------------------------------------------

MODELS = [
    {
        "role": "line",
        "name": "Chinese (song-line)",
        "type": 0,
        "tsv": "_Lines_Basic.tsv",
        "fields": ["Key", "SongSlug", "LineNo", "HanziPlain", "Pinyin",
                   "English", "Breakdown", "Audio", "PrevHanzi", "PrevAudio"],
        "templates": [("Recall-line", LINE_RECALL_Q, LINE_RECALL_A),
                      ("Reading", LINE_READING_Q, LINE_READING_A)],
        "cloze_ord": None,
        "req": [[0, "any", [3]], [1, "any", [3]]],
    },
    {
        "role": "cloze",
        "name": "Chinese (song-line-cloze)",
        "type": 1,
        "tsv": "_Lines_Cloze.tsv",
        "fields": ["Key", "SongSlug", "LineNo", "Hanzi", "Pinyin",
                   "English", "Breakdown", "Audio"],
        "templates": [("Cloze", CLOZE_Q, CLOZE_A)],
        "cloze_ord": 3,
        "req": [[0, "all", [3]]],
    },
    {
        "role": "block",
        "name": "Chinese (song-block)",
        "type": 1,
        "tsv": "_Blocks.tsv",
        "fields": ["Key", "SongSlug", "BlockNo", "Lines", "Pinyin",
                   "English", "Breakdown", "BlockAudio"],
        "templates": [("Block cloze", BLOCK_Q, BLOCK_A)],
        "cloze_ord": 3,
        "req": [[0, "all", [3]]],
    },
]

LATEX_PRE = ("\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n"
             "\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n"
             "\\setlength{\\parindent}{0in}\n\\begin{document}\n")
LATEX_POST = "\\end{document}"


def stable_uuid(seed: str) -> str:
    return str(uuid.uuid5(NS, seed))


def guid(seed: str) -> str:
    """10-char base91 guid (same shape Anki/CrowdAnki use), deterministic."""
    num = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    out = ""
    while num and len(out) < 10:
        num, rem = divmod(num, 91)
        out = _BASE91[rem] + out
    return out.rjust(10, _BASE91[0])


def read_tsv(path: Path) -> list[dict]:
    """Rows mapped by the file's own #columns header (Tags column included)."""
    cols = None
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#columns:"):
            cols = line[len("#columns:"):].split("\t")
        elif line and not line.startswith("#"):
            rows.append(line.split("\t"))
    if cols is None:
        raise SystemExit(f"{path}: no #columns directive")
    out = []
    for cells in rows:
        cells += [""] * (len(cols) - len(cells))
        out.append({cols[i]: cells[i] for i in range(len(cols))})
    return out


def build_model(m: dict, css: str) -> dict:
    flds = [{
        "collapsed": False, "description": "", "excludeFromSearch": False,
        "font": "Arial", "id": None, "media": [], "name": name, "ord": i,
        "plainText": False, "preventDeletion": False, "rtl": False,
        "size": 20, "sticky": False, "tag": None,
    } for i, name in enumerate(m["fields"])]

    tmpls = [{
        "afmt": afmt, "bafmt": "", "bfont": "", "bqfmt": "", "bsize": 0,
        "did": None, "id": None, "name": name, "ord": i, "qfmt": qfmt,
    } for i, (name, qfmt, afmt) in enumerate(m["templates"])]

    return {
        "__type__": "NoteModel",
        "crowdanki_uuid": stable_uuid("song-model:" + m["name"]),
        "css": css,
        "flds": flds,
        "latexPost": LATEX_POST,
        "latexPre": LATEX_PRE,
        "latexsvg": False,
        "name": m["name"],
        "originalId": None,
        "req": m["req"],
        "sortf": 0,            # sort browser rows by Key (field 0)
        "tags": [],
        "tmpls": tmpls,
        "type": m["type"],
        "vers": [],
    }


def build_notes(m: dict, rows: list[dict]) -> list[dict]:
    model_uuid = stable_uuid("song-model:" + m["name"])
    notes = []
    for r in rows:
        key = r["Key"]
        notes.append({
            "__type__": "Note",
            "fields": [r.get(f, "") for f in m["fields"]],
            "guid": guid(f"song-note-v1:{m['role']}:{key}"),
            "note_model_uuid": model_uuid,
            "tags": r.get("Tags", "").split(),
        })
    return notes


def deck_config(uuid_str: str) -> dict:
    """A neutral DeckConfig (FSRS params left empty → Anki defaults)."""
    return {
        "__type__": "DeckConfig",
        "answerAction": 0, "autoplay": True, "buryInterdayLearning": True,
        "crowdanki_uuid": uuid_str, "desiredRetention": 0.9, "dyn": False,
        "easyDaysPercentages": [1.0] * 7,
        "fsrsParams5": [], "fsrsParams6": [], "fsrsWeights": [],
        "ignoreRevlogsBeforeDate": "1970-01-01", "interdayLearningMix": 2,
        "lapse": {"delays": [10.0], "leechAction": 1, "leechFails": 8,
                  "minInt": 1, "mult": 0.0},
        "maxTaken": 60, "name": "chinese-songs",
        "new": {"bury": True, "delays": [10.0], "initialFactor": 2500,
                "ints": [1, 4, 0], "order": 1, "perDay": 20},
        "newGatherPriority": 0, "newMix": 1, "newPerDayMinimum": 0,
        "newSortOrder": 0, "questionAction": 0, "replayq": True,
        "rev": {"bury": True, "ease4": 1.3, "hardFactor": 1.2, "ivlFct": 1.0,
                "maxIvl": 36500, "perDay": 9999},
        "reviewOrder": 11, "secondsToShowAnswer": 0.0,
        "secondsToShowQuestion": 0.0, "sm2Retention": 0.9,
        "stopTimerOnAnswer": False, "timer": 0, "waitForAudio": True,
        "weightSearch": "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song-dir", required=True, type=Path,
                    help="songs/<slug> — must hold the 3 TSVs + media/")
    ap.add_argument("--deck-name", default=None,
                    help="override full deck name; default Chinese::Songs::<title_zh>")
    ap.add_argument("--no-copy-js", action="store_true",
                    help="don't copy _ruby.js / _song_ruby.js into media/")
    args = ap.parse_args()

    song_dir = args.song_dir.resolve()
    slug = song_dir.name
    media_dir = song_dir / "media"
    css = CSS_PATH.read_text(encoding="utf-8")

    # Deck name from source.yaml's title_zh (cheap parse — no yaml dep needed).
    title_zh = slug
    src = song_dir / "source.yaml"
    if src.exists():
        for line in src.read_text(encoding="utf-8").splitlines():
            if line.startswith("title_zh:"):
                title_zh = line.split(":", 1)[1].strip()
                break
    deck_name = args.deck_name or f"{DEFAULT_DECK_PARENT}::{title_zh}"

    # Find the TSV stem (e.g. Chinese_Song_Bu_Pa_Bu_Pa_Lines / _Blocks).
    note_models, notes = [], []
    for m in MODELS:
        matches = sorted(song_dir.glob("*" + m["tsv"]))
        if not matches:
            raise SystemExit(f"missing TSV *{m['tsv']} in {song_dir}")
        rows = read_tsv(matches[0])
        note_models.append(build_model(m, css))
        notes.extend(build_notes(m, rows))
        print(f"  {m['name']:<26} {len(rows):>2} notes  ({matches[0].name})")

    # Copy template JS deps into media/ so the import installs them too.
    if not args.no_copy_js:
        for js in (RUBY_JS, SONG_RUBY_JS):
            if js.exists():
                shutil.copy2(js, media_dir / js.name)
            else:
                print(f"  warn: {js} not found — JS dep not bundled")

    # media_files = every real file in media/ (flat) — mp3 clips, block combos
    # (incl. the JS-referenced front combos), and the JS deps. Subdirs skipped.
    media_files = sorted(p.name for p in media_dir.iterdir() if p.is_file())

    deck_cfg_uuid = stable_uuid("song-deckconfig")
    deck = {
        "__type__": "Deck",
        "children": [],
        "crowdanki_uuid": stable_uuid("song-deck:" + slug),
        "deck_config_uuid": deck_cfg_uuid,
        "deck_configurations": [deck_config(deck_cfg_uuid)],
        "desc": f"Song deck: {title_zh}. Generated from the song TSVs by "
                f"songs/_pipeline/build_crowdanki.py.",
        "desiredRetention": None,
        "dyn": 0, "extendNew": 0, "extendRev": 0,
        "media_files": media_files,
        "name": deck_name,
        "newLimit": None, "newLimitToday": None,
        "note_models": note_models,
        "notes": notes,
        "reviewLimit": None, "reviewLimitToday": None,
    }

    out = song_dir / "deck.json"
    out.write_text(json.dumps(deck, ensure_ascii=False, indent=4) + "\n",
                   encoding="utf-8")
    print(f"wrote {out}")
    print(f"  deck name   : {deck_name}")
    print(f"  models      : {len(note_models)}  notes: {len(notes)}")
    print(f"  media_files : {len(media_files)}")


if __name__ == "__main__":
    main()
