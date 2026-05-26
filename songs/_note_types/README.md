# Anki note types for song decks

Setup guide for the note types the song pipeline targets. Create these once; each new song just imports its TSVs into the matching note types.

## The note types

| Note type | Anki base | Cards per note | Source TSV |
|-----------|-----------|----------------|------------|
| [`SongLineBasic`](SongLineBasic.md) | Basic | Reading (1) + Recall-line (0-1) | `…_Lines_Basic.tsv` |
| [`SongLineCloze`](SongLineCloze.md) | Cloze | Cloze (N per line, varies) | `…_Lines_Cloze.tsv` |
| [`SongBlock`](SongBlock.md) | Cloze | Block cloze (N per block, varies) | `…_Blocks.tsv` |

`SongLineBasic` + `SongLineCloze` together cover the SongLine concept. They live in separate note types because Anki's Cloze type can't host non-cloze card templates.

## One-time installs into Anki's `collection.media/`

These JavaScript files are referenced by the song card templates via `<script src="…">`. Anki looks them up in `collection.media/`. The leading underscore in their names keeps Anki from purging them as unused media.

| File | Source path in this repo | Purpose |
|------|--------------------------|---------|
| `_ruby.js` | `note_type/Chinese_anki_decks/_ruby.js` | Shared with word decks. Builds `<ruby>` markup from `data-hanzi` + `data-pinyin` attributes. |
| `_song_ruby.js` | `songs/_note_types/_song_ruby.js` | Song-specific. Adds `mountElement` (cloze-aware single line) + `mountLines` (multi-line block cards). |

To find the folder: in Anki, click the "Files" link at the bottom of the Files menu, or check `%APPDATA%\Anki2\<profile>\collection.media\` on Windows.

If you've never set up the word decks, copy `_ruby.js` from this repo into `collection.media/` now.

## Setup order

1. Drop `_ruby.js` and `_song_ruby.js` into `collection.media/`.
2. Open Anki → Tools → Manage Note Types → Add.
3. For each note type (Basic for `SongLineBasic`, Cloze for the other two): create it, follow the per-type `.md` file to rename fields and paste card templates + [styling.css](styling.css).
4. Set each note type's **Sort field** to `Key` (note type editor → Cards).

## Deck / order conventions

- One Anki deck per song, e.g. `Chinese::Songs::一剪梅`.
- Deck options → **New card order: "Order added"** so cards play out top-to-bottom in line order.
- Deck options → **Bury related new + review** so siblings of the same note don't repeat in one session.

## Card ordering options

Within a single import session, Anki's "Order added" assigns lower note positions to whatever file is imported first. New cards are drawn by note position. With the three TSVs as-is, importing them in this order:

```
Lines_Basic.tsv   → SongLineBasic notes  (positions 1..N)
Lines_Cloze.tsv   → SongLineCloze notes  (positions N+1..2N)
Blocks.tsv        → SongBlock notes      (positions 2N+1..)
```

…produces this overall flow when you study the deck:

```
all Reading + Recall (sibling-buried, so 1 per line per day)
  → all Cloze cards (sibling-buried among each line's clozes)
    → all Block cards (sibling-buried among each block's slots)
```

**If you want strict Reading → Cloze → Recall ordering**, two paths:

- **Manual reposition** (chosen for now): after import, use Anki's Browse → Cards → Reposition to set explicit new-card positions per card type. Tedious per song but full control.
- **Split `SongLineBasic` into `SongLineReading` + `SongLineRecall`** (not implemented): each as a single-template Basic note type, imported in order. The `build_tsv.py` builder would need to emit four TSVs per song instead of three. Easy to add later if manual repositioning becomes painful.

## Sibling burying caveat

Anki's sibling burying only works within the same note. Across note types (Basic + Cloze + Block), line N has separate notes — they are NOT siblings of each other. The same line may surface in two cards in one session. The deck-wide "Order added" flow above usually staggers them across days, so it's mild.

## Media files

After importing the TSVs, copy `media/*.mp3` from each song's dir into `collection.media/`. All audio refs use plain filenames (`[sound:yi_jian_mei_001.mp3]`), so Anki resolves them via that folder.

## Field-list cheat sheet

**SongLineBasic** (Basic):
```
Key
SongSlug
LineNo
HanziPlain
Pinyin
English
Breakdown
Audio
PrevHanzi
PrevAudio
```

**SongLineCloze** (Cloze):
```
Key
SongSlug
LineNo
Hanzi
Pinyin
English
Breakdown
Audio
```

**SongBlock** (Cloze):
```
Key
SongSlug
BlockNo
Lines
Pinyin
English
Breakdown
BlockAudio
```
