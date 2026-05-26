# Song lyric decks

Personal Anki decks built from Chinese songs. One deck per song. Pipeline turns a YouTube URL + raw lyrics text into a line-aligned, audio-sliced TSV ready for Anki import.

**Scope:** sandbox for now. Per-song schema and note-type design are still in flux; intentionally diverges from the word-deck conventions in the repo root (`Chinese_Core_Conversation.tsv`, etc.). Once the design lands we'll write up the final note types here.

## Directory layout

```
songs/
├── .gitignore
├── README.md                         (this file)
├── _pipeline/                        shared scripts
│   ├── cache/
│   │   └── cedict_ts.u8              CC-CEDICT (gitignored — regenerable)
│   ├── convert.py                    traditional → simplified
│   ├── align.py                      stable-ts forced alignment
│   ├── slice.py                      ffmpeg per-line clip cutter
│   ├── gloss.py                      CC-CEDICT-based Breakdown generator
│   ├── cloze_pick.py                 jieba-based cloze candidate picker
│   ├── block_plan.py                 chunks lines into N-line blocks
│   ├── combo_audio.py                bakes block-cloze combo mp3s
│   ├── build_tsv.py                  SongLine TSV emitter
│   └── build_blocks_tsv.py           SongBlock TSV emitter
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
    ├── Chinese_Song_<X>_Lines.tsv     SongLine notes — Cloze note type
    └── Chinese_Song_<X>_Blocks.tsv    SongBlock notes — Cloze note type
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

# 12. Emit SongLine TSV (one note per line, cloze + reading + recall cards).
python songs/_pipeline/build_tsv.py \
  --aligned     $DIR/aligned.json \
  --english     $DIR/english.txt \
  --breakdown   $DIR/breakdown.txt \
  --cloze-plan  $DIR/cloze_plan.yaml \
  --out         $DIR/Chinese_Song_<Title>_Lines.tsv \
  --prefix      $SLUG \
  --song-slug   $SLUG \
  --tag song --tag song-$SLUG --tag artist-<slug>

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

# 14. Copy $DIR/media/*.mp3 into Anki's collection.media/, then import BOTH
#     TSVs (Lines first — its lower note positions ensure Anki shows
#     line-level cards before block-cloze cards).
```

## Anki import notes

- TSV directive block sets columns + tag column. Anki picks them up automatically.
- Audio refs are `[sound:<slug>_NNN.mp3]`. Files must live in Anki's `collection.media/`.
- Re-importing the same TSV updates rows by first column (Hanzi); no duplicate notes.

## Pipeline behavior — gotchas

- **`opencc` t2s leaves some valid traditional chars alone** (e.g. `翦` for 一翦梅). `convert.py` has an `EXTRA_FIXUPS` table to patch these. Extend it when new oddities appear.
- **stable-ts alignment is line-level** — accuracy is plausible-ish for slow ballads, drifts on fast / rap / heavy instrumental tracks. Always spot-check a few clips per song.
- **`slice.py` tail padding** defaults to 1.5s but auto-caps at `next_line.start − 0.05` to avoid overlap. The final line of the song gets the full free pad.
- **Dedup rule**: same Hanzi line never produces two notes. Important when alignment covers a repeated chorus pass.
- **`gloss.py` is a baseline, not final**. `CHAR_OVERRIDES` table holds curated per-char picks where CC-CEDICT's first sense is pedagogically weak. Add to it as you spot bad glosses. For polysemous chars in unusual senses, hand-edit `breakdown.txt` before running `build_tsv.py`.

## Scope reminder

Songs are **literary register** — poetic, often classical-leaning. They are NOT a substitute for the word decks at repo root. Pedagogical value: fun, listening practice, sing-along recall. Efficiency value: low. Treat as flavor on top of normal study.
