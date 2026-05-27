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

## Card ordering — recommended import order

Anki picks new cards by `(note position, then card-template index)`. Note position = order added at import time. So the file you import first gets the lowest positions and its cards appear first in the new-card queue.

For pedagogical flow (musical familiarity → sequential recall → meaning), import in this order:

```
1. Lines_Cloze.tsv   → SongLineCloze   (word-level cloze cards introduced first)
2. Blocks.tsv        → SongBlock       (whole-line block cloze cards next)
3. Lines_Basic.tsv   → SongLineBasic   (Recall-line as Card 1, Reading as Card 2)
```

Result in the deck's new-card queue:

```
cloze cards → block cards → recall cards → reading cards
```

Inside SongLineBasic the two templates are ordered Recall (Card 1) → Reading (Card 2) so within each note the Recall card surfaces before the Reading card.

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
