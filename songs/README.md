# Song lyric decks

Personal Anki decks built from Chinese songs. One deck per song. Pipeline turns a YouTube URL + raw lyrics text into a line-aligned, audio-sliced TSV ready for Anki import.

**Scope:** sandbox for now. Per-song schema and note-type design are still in flux; intentionally diverges from the word-deck conventions in the repo root (`Chinese_Core_Conversation.tsv`, etc.). Once the design lands we'll write up the final note types here.

## Directory layout

```
songs/
├── .gitignore
├── README.md                         (this file)
├── _note_types/                      Anki note-type setup guides (one-time)
│   ├── README.md                     overview + setup order
│   ├── styling.css                   shared CSS for all 3 note types
│   ├── SongLineBasic.md              Reading + Recall-line templates
│   ├── SongLineCloze.md              word-level cloze template
│   └── SongBlock.md                  whole-line block cloze template
├── _pipeline/                        shared scripts
│   ├── cache/
│   │   └── cedict_ts.u8              CC-CEDICT (gitignored — regenerable)
│   ├── convert.py                    traditional → simplified
│   ├── align.py                      stable-ts forced alignment
│   ├── slice.py                      ffmpeg per-line clip cutter
│   ├── gloss.py                      CC-CEDICT-based Breakdown generator
│   ├── cloze_pick.py                 jieba-based cloze candidate picker
│   ├── block_plan.py                 chunks lines into N-line blocks (dedups repeats)
│   ├── combo_audio.py                bakes block-cloze combo mp3s
│   ├── build_tsv.py                  SongLine TSV emitter
│   ├── build_blocks_tsv.py           SongBlock TSV emitter
│   ├── cleanup_media.py              prunes audio clips not referenced by any TSV
│   └── build_crowdanki.py            CrowdAnki deck.json emitter (one-click import)
└── <song_slug>/                      one dir per song
    ├── source.yaml                   title, artist, url, raw lyrics
    ├── audio.webm                    yt-dlp original (gitignored)
    ├── audio.mp3                     ffmpeg-converted, full song (gitignored — regenerable)
    ├── lyrics_traditional.txt        one line per row, as found on the web
    ├── lyrics_simplified.txt         output of convert.py
    ├── english.txt                   rough English glosses (manual)
    ├── breakdown.txt                 output of gloss.py
    ├── aligned.json                  output of align.py (line → [start, end])
    ├── cloze_plan.yaml                output of cloze_pick.py (suggested + selected_clozes per line)
    ├── blocks.yaml                    output of block_plan.py (N-line chunks)
    ├── media/                        sliced per-line clips + block-cloze combos
    │   ├── <song_slug>_NNN.mp3            per-line clips (14 for yi_jian_mei)
    │   ├── <song_slug>_block_<BB>_c<K>.mp3 block-cloze combos (1 per blanked slot)
    │   └── _silence/                  silence file cache (gitignored)
    ├── Chinese_Song_<X>_Lines_Basic.tsv   → SongLineBasic note type
    ├── Chinese_Song_<X>_Lines_Cloze.tsv   → SongLineCloze note type
    ├── Chinese_Song_<X>_Blocks.tsv        → SongBlock note type
    └── deck.json                          CrowdAnki one-click import (generated; TSVs stay canonical)
```

## Tooling required

| Tool | Why | Install |
|------|-----|---------|
| Python 3.11+ | runs the pipeline | system |
| `ffmpeg` | mp3 conversion + slicing | `winget install Gyan.FFmpeg` (Windows), `brew install ffmpeg` (mac) |
| pip deps | `yt-dlp pypinyin opencc-python-reimplemented stable-ts` | `pip install …` |

First run of `align.py` downloads the Whisper `small` model (~460MB) into the user-level cache.

## Adding a new song — full pipeline

```bash
SLUG=<song_slug>           # e.g. yi_jian_mei
DIR=songs/$SLUG
mkdir -p $DIR/media

# 1. Write source.yaml: title, artist, url, paste raw lyrics (any script).
$EDITOR $DIR/source.yaml

# 2. Pull raw lyrics into lyrics_traditional.txt (one Hanzi line per row).
$EDITOR $DIR/lyrics_traditional.txt

# 3. Traditional → simplified.
python songs/_pipeline/convert.py \
  --in  $DIR/lyrics_traditional.txt \
  --out $DIR/lyrics_simplified.txt

# 4. Download audio + transcode to mp3.
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  -o "$DIR/audio.%(ext)s" "<youtube_url>"
# (if ffmpeg postprocess fails, run the ffmpeg conversion manually)

# 5. Forced-align lyric lines to audio timestamps.
python songs/_pipeline/align.py \
  --audio   $DIR/audio.mp3 \
  --lyrics  $DIR/lyrics_simplified.txt \
  --out     $DIR/aligned.json \
  --model   small

# 6. Slice mp3 into per-line clips.
python songs/_pipeline/slice.py \
  --audio    $DIR/audio.mp3 \
  --aligned  $DIR/aligned.json \
  --out-dir  $DIR/media \
  --prefix   $SLUG \
  --ffmpeg   ffmpeg

# 7. Auto-generate per-char Breakdown via CC-CEDICT.
python songs/_pipeline/gloss.py \
  --lyrics $DIR/lyrics_simplified.txt \
  --out    $DIR/breakdown.txt

# 8. Hand-write rough English glosses (1 line per row, same order).
$EDITOR $DIR/english.txt

# 9. Auto-suggest cloze candidates per line; review + edit the YAML.
python songs/_pipeline/cloze_pick.py \
  --lyrics    $DIR/lyrics_simplified.txt \
  --out       $DIR/cloze_plan.yaml \
  --song-slug $SLUG
$EDITOR $DIR/cloze_plan.yaml   # tweak `selected_clozes` per line

# 10. Chunk lines into N-line blocks for SongBlock cards.
python songs/_pipeline/block_plan.py \
  --aligned   $DIR/aligned.json \
  --out       $DIR/blocks.yaml \
  --song-slug $SLUG \
  --block-size 4

# 11. Pre-bake block-cloze combo audio (line clips + silence in blanked slot).
python songs/_pipeline/combo_audio.py \
  --blocks    $DIR/blocks.yaml \
  --media-dir $DIR/media \
  --prefix    $SLUG \
  --ffmpeg ffmpeg --ffprobe ffprobe

# 12. Emit SongLine TSVs (splits into Basic + Cloze because Anki's
#     Cloze note type can't host non-cloze card templates).
python songs/_pipeline/build_tsv.py \
  --aligned     $DIR/aligned.json \
  --english     $DIR/english.txt \
  --breakdown   $DIR/breakdown.txt \
  --cloze-plan  $DIR/cloze_plan.yaml \
  --out-stem    $DIR/Chinese_Song_<Title>_Lines \
  --prefix      $SLUG \
  --song-slug   $SLUG \
  --tag song --tag song-$SLUG --tag artist-<slug>
# → emits  ..._Lines_Basic.tsv  AND  ..._Lines_Cloze.tsv

# 13. Emit SongBlock TSV (one note per block, whole-line cloze cards).
python songs/_pipeline/build_blocks_tsv.py \
  --blocks      $DIR/blocks.yaml \
  --aligned     $DIR/aligned.json \
  --english     $DIR/english.txt \
  --breakdown   $DIR/breakdown.txt \
  --out         $DIR/Chinese_Song_<Title>_Blocks.tsv \
  --prefix      $SLUG \
  --song-slug   $SLUG \
  --tag song --tag song-$SLUG --tag artist-<slug>

# 14. Prune audio clips not referenced by any TSV (chorus-repeat lines,
#     orphan combos from deduped blocks).
python songs/_pipeline/cleanup_media.py \
  --media-dir $DIR/media \
  --prefix    $SLUG \
  --blocks    $DIR/blocks.yaml \
  --line-tsv  $DIR/Chinese_Song_<Title>_Lines_Cloze.tsv

# 15. Copy $DIR/media/*.mp3 into Anki's collection.media/, then import the
#     TSVs in order (lowest position = first introduced to new-card queue):
#       ..._Lines_Cloze.tsv  →  SongLineCloze  (word-level cloze; first)
#       ..._Blocks.tsv       →  SongBlock      (whole-line block cloze)
#       ..._Lines_Basic.tsv  →  SongLineBasic  (Recall-line + Reading; last)
#     See songs/_note_types/README.md for one-time note-type setup.
```

The whole flow is also wrapped in a Claude Code skill — invoke
`/song-deck-add` to walk a song through end-to-end with the two
interactive review checkpoints (cloze plan + English glosses).

## Anki import notes

- TSV directive block sets columns + tag column. Anki picks them up automatically.
- Audio refs are `[sound:<slug>_NNN.mp3]`. Files must live in Anki's `collection.media/`.
- Re-importing the same TSV updates rows by first column (Hanzi); no duplicate notes.
- **CrowdAnki one-click alternative** (`build_crowdanki.py` → `songs/<slug>/deck.json`): a self-contained CrowdAnki deck bundling all notes, the audio, and the template JS (`_ruby.js` / `_song_ruby.js`). Import via CrowdAnki → *Import from folder* → the song dir; it installs everything — no manual `collection.media` copy. The 3 note types are **pinned** to your real Anki note types (captured verbatim in [`_note_types/crowdanki_models.json`](_note_types/crowdanki_models.json), same UUIDs), so a re-import updates them in place and never makes duplicates — only the notes change. Re-export + overwrite that file if you ever edit a note type in Anki. Deck config is **referenced but not imported** (`中文-song` by UUID), so your constantly-retraining FSRS params are never reset. Deck name defaults to `中文::神曲::<title_zh>`. Stable per-note GUIDs mean re-imports update in place. The TSVs stay the source of truth; the JSON is regenerated from them.

## Pipeline behavior — gotchas

- **`opencc` t2s leaves some valid traditional chars alone** (e.g. `翦` for 一翦梅). `convert.py` has an `EXTRA_FIXUPS` table to patch these. Extend it when new oddities appear.
- **stable-ts alignment is line-level** — accuracy is plausible-ish for slow ballads, drifts on fast / rap / heavy instrumental tracks. Always spot-check a few clips per song.
- **`slice.py` tail padding** defaults to 1.5s but auto-caps at `next_line.start − 0.05` to avoid overlap. The final line of the song gets the full free pad.
- **Dedup rule**: same Hanzi line never produces two notes. Important when alignment covers a repeated chorus pass.
- **`gloss.py` is a baseline, not final**. `CHAR_OVERRIDES` table holds curated per-char picks where CC-CEDICT's first sense is pedagogically weak. Add to it as you spot bad glosses. For polysemous chars in unusual senses, hand-edit `breakdown.txt` before running `build_tsv.py`.
- **Embedded (code-switched) English is kept inline, not stripped.** `build_tsv.line_pinyin` runs pypinyin with `errors="ignore"` (one syllable *per Han char*), and the ruby builders (`_ruby.js` `buildRuby`, `_song_ruby.js` `countHan`) match token-count to **Han-char count only** and emit non-Han as plain inline text — so a sung `HELLO` or an English rap hook renders inline with no pinyin and never desyncs the line. The helpers that *do* ignore English: `gloss.py` (no Breakdown entry for English) and `cloze_pick.py` (jieba tags it `x`, never suggested) — but `inject_clozes` is a raw substring replace, so you can hand-add a load-bearing English word to `selected_clozes`. Only English *translation* lines (lyric-site glosses) get stripped; lexical sung English stays.

## Scope reminder

Songs are **literary register** — poetic, often classical-leaning. They are NOT a substitute for the word decks at repo root. Pedagogical value: fun, listening practice, sing-along recall. Efficiency value: low. Treat as flavor on top of normal study.
