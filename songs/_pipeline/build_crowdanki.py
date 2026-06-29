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

Note GUIDs are preserved across regenerations — reused from the existing
deck.json (or an export passed via --guid-source), else minted deterministically
from role + the TSV Key. So re-imports always update in place, never duplicate.
Deck UUID is derived from the song slug.

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
# ORDER MATTERS: notes are emitted in this order, and Anki's new-card queue
# follows note creation (= array) order. cloze -> block -> basic matches the
# user's existing exported decks (一剪梅 / 干嘛) and the pipeline README, so the
# new-card flow is: word cloze -> block cloze -> recall -> reading.
ROLE_MAP = [
    ("cloze", "Chinese (song-line-cloze)", "_Lines_Cloze.tsv"),
    ("block", "Chinese (song-block)",      "_Blocks.tsv"),
    ("line",  "Chinese (song-line)",       "_Lines_Basic.tsv"),
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


def needed_media(notes: list[dict], block_uuid: str, slug: str) -> set[str]:
    """Filenames actually used by the deck: every [sound:] reference, the
    block-cloze combos (c1..cK + full per block — JS-picked, so not in any
    field), and the two template JS deps. Excludes orphan clips left in media/."""
    snd = re.compile(r"\[sound:([^\]]+)\]")
    want: set[str] = {"_ruby.js", "_song_ruby.js"}
    for n in notes:
        for f in n["fields"]:
            want |= set(snd.findall(f))
        if n["note_model_uuid"] == block_uuid:
            bno = int(n["fields"][2])
            k = n["fields"][3].count("{{c")
            for i in range(1, k + 1):
                want.add(f"{slug}_block_{bno:02d}_c{i}.mp3")
            want.add(f"{slug}_block_{bno:02d}_full.mp3")
    return want


def build_notes(role: str, model: dict, rows: list[dict],
                guid_map: dict) -> list[dict]:
    field_order = [f["name"] for f in model["flds"]]
    model_uuid = model["crowdanki_uuid"]
    notes = []
    for r in rows:
        key = r["Key"]
        # Reuse an existing GUID for this (model, Key) if we have one, else mint
        # a deterministic one. Keeps re-imports updating in place, never duping.
        g = guid_map.get((model_uuid, key)) or guid(f"song-note-v1:{role}:{key}")
        notes.append({
            "__type__": "Note",
            "fields": [r.get(f, "") for f in field_order],
            "guid": g,
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
    ap.add_argument("--guid-source", type=Path, default=None,
                    help="CrowdAnki deck.json (e.g. an Anki export) to copy note "
                         "GUIDs from, matched by (note model, Key). Defaults to the "
                         "existing target deck.json so re-runs stay stable; pass an "
                         "export to seed GUIDs for an already-in-Anki deck.")
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

    # Preserve note GUIDs across regenerations: from --guid-source if given,
    # else from the existing target deck.json. Keyed by (note model uuid, Key).
    guid_src = args.guid_source or (song_dir / "deck.json")
    guid_map: dict = {}
    if guid_src.exists():
        prev = json.loads(guid_src.read_text(encoding="utf-8"))
        for n in prev.get("notes", []):
            f = n.get("fields") or []
            if f:
                guid_map[(n["note_model_uuid"], f[0])] = n["guid"]
        print(f"  preserving {len(guid_map)} GUID(s) from {guid_src.name}")

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
        notes.extend(build_notes(role, model, rows, guid_map))
        print(f"  {model_name:<26} {len(rows):>2} notes  ({matches[0].name})")

    # Copy template JS deps into media/ so the import installs them too.
    if not args.no_copy_js:
        for js in (RUBY_JS, SONG_RUBY_JS):
            if js.exists():
                shutil.copy2(js, media_dir / js.name)
            else:
                print(f"  warn: {js} not found — JS dep not bundled")

    # media_files = only what the deck actually uses (referenced [sound:] clips,
    # JS-derived block combos, JS deps) — not every file in media/, so orphan
    # clips are excluded. Referenced-but-absent files (e.g. a pre-existing broken
    # clip) are reported and skipped so a missing-media entry can't fail import.
    block_uuid = models["Chinese (song-block)"]["crowdanki_uuid"]
    want = needed_media(notes, block_uuid, slug)
    present = {p.name for p in media_dir.iterdir() if p.is_file()}
    missing = sorted(f for f in want if f not in present)
    media_files = sorted(f for f in want if f in present)
    if missing:
        print(f"  WARNING: {len(missing)} referenced media file(s) absent on disk "
              f"— not bundled: {missing}")

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
