#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a CrowdAnki `deck.json` for one song from its three Lines/Blocks TSVs.

The TSVs stay the source of truth; this is a *second* export format layered on
top so the deck imports in one click via the CrowdAnki add-on (no manual
collection.media copy, no per-note-type template paste).

Note types are PINNED to the user's real Anki note types, captured verbatim in
`songs/_note_types/crowdanki_models.json` (exported from their collection):

  Chinese (song-line)         Basic  (type 0)  — Recall + Reading cards
  Chinese (song-line-cloze)   Cloze  (type 1)  — word-level cloze
  Chinese (song-block)        Cloze  (type 1)  — whole-line block cloze

Because the model UUIDs + definitions match what's already in Anki, a re-import
UPDATES those note types in place (it never creates duplicates) and only the
NOTES change. Keep crowdanki_models.json in sync if you ever edit a note type
in Anki (re-export and overwrite that file).

Deck config: CrowdAnki requires the referenced config to be PRESENT in the file
(otherwise "deck config uuid not present" — CrowdAnki bug #106). We include the
user's real `中文-song` options group (songs/_note_types/crowdanki_deck_config.json,
their exact settings) but with the auto-trained FSRS weight arrays stripped
(fsrsParams5 / fsrsParams6 / fsrsWeights). Intent: the deck auto-assigns to
中文-song and the constantly-retraining weights are not carried (so they can't be
reset to a stale value on import). CONFIRMED by test import: CrowdAnki leaves the
in-collection FSRS weights untouched when they're omitted, so a re-import never
resets them.

Note GUIDs are deterministic (role + the TSV Key), so re-imports update in
place. Deck UUID is derived from the song slug.

Run:  python songs/_pipeline/build_crowdanki.py --song-dir songs/<slug>
Deps: standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
MODELS_JSON = NOTE_TYPES_DIR / "crowdanki_models.json"
DECK_CONFIG_JSON = NOTE_TYPES_DIR / "crowdanki_deck_config.json"
SONG_RUBY_JS = NOTE_TYPES_DIR / "_song_ruby.js"
RUBY_JS = SONGS_DIR.parent / "note_type" / "Chinese_anki_decks" / "_ruby.js"

# Fixed namespace so uuid5() (deck UUID) is reproducible across runs.
NS = uuid.UUID("a1b2c3d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d")

_BASE91 = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "!#$%&()*+,-./:;<=>?@[]^_`{|}~"
)

DEFAULT_DECK_PARENT = "中文::神曲"


# role -> (model name in crowdanki_models.json, TSV filename suffix)
ROLE_MAP = [
    ("line",  "Chinese (song-line)",       "_Lines_Basic.tsv"),
    ("cloze", "Chinese (song-line-cloze)", "_Lines_Cloze.tsv"),
    ("block", "Chinese (song-block)",      "_Blocks.tsv"),
]


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


def build_notes(role: str, model: dict, rows: list[dict]) -> list[dict]:
    field_order = [f["name"] for f in model["flds"]]
    model_uuid = model["crowdanki_uuid"]
    notes = []
    for r in rows:
        key = r["Key"]
        notes.append({
            "__type__": "Note",
            "fields": [r.get(f, "") for f in field_order],
            "guid": guid(f"song-note-v1:{role}:{key}"),
            "note_model_uuid": model_uuid,
            "tags": sorted(r.get("Tags", "").split()),
        })
    return notes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song-dir", required=True, type=Path,
                    help="songs/<slug> — must hold the 3 TSVs + media/")
    ap.add_argument("--deck-name", default=None,
                    help="override full deck name; default 中文::神曲::<title_zh>")
    ap.add_argument("--no-copy-js", action="store_true",
                    help="don't copy _ruby.js / _song_ruby.js into media/")
    args = ap.parse_args()

    song_dir = args.song_dir.resolve()
    slug = song_dir.name
    media_dir = song_dir / "media"
    models = json.loads(MODELS_JSON.read_text(encoding="utf-8"))

    # Deck name from source.yaml's title_zh (cheap parse — no yaml dep needed).
    title_zh = slug
    src = song_dir / "source.yaml"
    if src.exists():
        for line in src.read_text(encoding="utf-8").splitlines():
            if line.startswith("title_zh:"):
                title_zh = line.split(":", 1)[1].strip()
                break
    deck_name = args.deck_name or f"{DEFAULT_DECK_PARENT}::{title_zh}"

    note_models, notes = [], []
    for role, model_name, tsv_suffix in ROLE_MAP:
        if model_name not in models:
            raise SystemExit(f"{MODELS_JSON}: missing model {model_name!r}")
        model = models[model_name]
        matches = sorted(song_dir.glob("*" + tsv_suffix))
        if not matches:
            raise SystemExit(f"missing TSV *{tsv_suffix} in {song_dir}")
        rows = read_tsv(matches[0])
        note_models.append(model)
        notes.extend(build_notes(role, model, rows))
        print(f"  {model_name:<26} {len(rows):>2} notes  ({matches[0].name})")

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

    deck_config = json.loads(DECK_CONFIG_JSON.read_text(encoding="utf-8"))
    deck = {
        "__type__": "Deck",
        "children": [],
        "crowdanki_uuid": str(uuid.uuid5(NS, "song-deck:" + slug)),
        "deck_config_uuid": deck_config["crowdanki_uuid"],
        "deck_configurations": [deck_config],
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
    print(f"  models      : {len(note_models)} (pinned)  notes: {len(notes)}")
    print(f"  deck config : {deck_config['name']} {deck_config['crowdanki_uuid']} (FSRS weights omitted)")
    print(f"  media_files : {len(media_files)}")


if __name__ == "__main__":
    main()
