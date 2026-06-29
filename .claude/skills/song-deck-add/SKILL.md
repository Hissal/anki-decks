---
name: song-deck-add
description: >
  Use when the user wants to build an Anki deck from a Chinese song —
  triggers on /song-deck-add, "add a song", "build a deck for <song>",
  "make a song deck", or any request that pairs a song title/URL with
  raw lyrics. Walks the full songs/ pipeline (convert → align → slice →
  gloss → cloze pick → block plan → combo audio → TSV emit → media
  cleanup) with two interactive review checkpoints (cloze plan + English
  glosses). End result: three importable TSVs + a CrowdAnki deck.json
  (one-click import) + a media/ folder ready to drop into Anki's
  collection.media/.
---

# song-deck-add

Builds a per-song Anki deck under `songs/<slug>/` using the existing
song pipeline scripts in `songs/_pipeline/`. The pipeline is already
debugged for two reference songs (`yi_jian_mei`, `ganma`); this skill is
the orchestrator that knows the canonical order, the review
checkpoints, and where to inspect quality.

## When to activate

Activate when **any** of these is true:

- User invokes `/song-deck-add` or asks to "add a song", "build a song
  deck", "make a deck for <title>", etc.
- User pastes a song title + URL + lyrics block in one message.
- User says "let's do another song" mid-conversation about songs.

If ambiguous, ask once: **"Build a full song deck?"** before starting.

## Read these first (every invocation)

- `songs/README.md` — pipeline overview + per-step CLI invocation,
  source of truth for the command sequence.
- `songs/_note_types/README.md` — the Anki side; useful for explaining
  setup to a user who hasn't created the note types yet.
- `songs/yi_jian_mei/` and `songs/ganma/` — reference outputs to model
  the directory layout against.

If `songs/_pipeline/cache/cedict_ts.u8` is missing, fetch it first
(see step 2 below).

## Gather inputs

The skill needs four things from the user:

1. **Song title** (Chinese + English; English doubles as slug source).
2. **Artist** (Chinese + English).
3. **Audio URL** (YouTube, Bilibili — anything `yt-dlp` understands).
4. **Lyrics** — raw text, one line per lyric line, blank lines and
   English *translation* lines OK in the paste; the skill strips those
   out. **Lexical English that is itself sung** (a "HELLO", an English
   rap hook) is **kept inline** — see "Embedded English" below.

If any is missing, ask once. If lyrics look traditional, note that and
flag for `convert.py`.

## Choose a slug

- Use a lowercase, hyphen-or-underscore-separated short ID derived from
  the English title (e.g. `yi_jian_mei`, `ganma`, `qing_hua_ci`).
- Keep it short — it appears in audio filenames and TSV keys.

## Pipeline (canonical order)

Run each step, inspect output, escalate to user only at the **review
checkpoints** marked below.

```
0. Set up dir
   mkdir -p songs/<slug>/media
   write songs/<slug>/source.yaml   (title_zh, title_pinyin, title_en,
                                     artist_zh, artist_en, url, notes)
   write songs/<slug>/lyrics_simplified.txt
     - one line per lyric line
     - strip English *translation* lines, blank lines, and non-lexical
       ad-libs (la-la / na-na / the "MAI-A-HEE" hook type)
     - KEEP lexical English sung as part of a line (see "Embedded
       English" below); leave one space between an English token and
       adjacent Hanzi for readability
     - if input was traditional: write lyrics_traditional.txt first,
       then run convert.py to produce lyrics_simplified.txt
     - normalize whitespace inside lines (collapse internal spaces; a
       single space around a kept English token is fine)

1. Audio
   python -m yt_dlp -x --audio-format mp3 --audio-quality 0 \
     --ffmpeg-location <ffmpeg-dir> \
     -o "songs/<slug>/audio.%(ext)s" "<url>"
   If extract conversion fails, fall back to manual ffmpeg:
     ffmpeg -y -i songs/<slug>/audio.webm ... songs/<slug>/audio.mp3

2. Forced align (stable-ts whisper "small")
   python songs/_pipeline/align.py \
     --audio songs/<slug>/audio.mp3 \
     --lyrics songs/<slug>/lyrics_simplified.txt \
     --out songs/<slug>/aligned.json \
     --model small

   First run downloads the ~500 MB Whisper "small" model. Subsequent
   runs reuse the cache.

   **Sanity-check the alignment.** Look for: (a) plausible spacing
   (lines shouldn't all be 0.1s long), (b) total duration matches
   audible end of lyrics, (c) gaps between lines are sane.

3. Slice
   python songs/_pipeline/slice.py \
     --audio songs/<slug>/audio.mp3 \
     --aligned songs/<slug>/aligned.json \
     --out-dir songs/<slug>/media \
     --prefix <slug> \
     --ffmpeg <ffmpeg-bin>

   Default padding: 0.15s head, 1.50s tail (auto-capped to next-line
   start - 0.05s). Bump --pad-tail if the song is exceptionally slow.

4. Auto-gloss per-char Breakdown
   python songs/_pipeline/gloss.py \
     --lyrics songs/<slug>/lyrics_simplified.txt \
     --out songs/<slug>/breakdown.txt

   If many chars come back as "?" or with weak glosses, consider
   extending CHAR_OVERRIDES in `gloss.py` — but only for chars that are
   common across multiple songs. Per-song outliers are user-editable
   directly in breakdown.txt.

5. Auto-suggest cloze candidates
   python songs/_pipeline/cloze_pick.py \
     --lyrics songs/<slug>/lyrics_simplified.txt \
     --out songs/<slug>/cloze_plan.yaml \
     --song-slug <slug> --top-n 2

   ◇◇◇ REVIEW CHECKPOINT #1 — Cloze plan ◇◇◇

   - Print the per-line suggestions table.
   - Inspect every line for jieba mis-segmentations (the classic one:
     reduplicated chars like `睡睡睡睡睡` getting grouped as `睡睡`).
   - Propose edits: add poetic / song-thematic words, drop boring
     particles, swap obvious-but-meaningless picks for the line's
     load-bearing verb or noun.
   - For lines that are duplicates of earlier lines (build_tsv will
     dedup them), the cloze entry is unused — don't bother curating.
   - Show user the proposed-edits side-by-side table; await approval.
   - Apply edits to `selected_clozes` field of the YAML (preserving
     `suggested_clozes` + `_debug` as audit trail).

6. Block plan (chunks lines into N-line blocks, dedups by content)
   python songs/_pipeline/block_plan.py \
     --aligned songs/<slug>/aligned.json \
     --out songs/<slug>/blocks.yaml \
     --song-slug <slug> --block-size 4

   The dedup pass collapses repeated chorus/refrain blocks
   automatically. Default block-size is 4; bump or shrink if the song's
   structure clearly calls for different stanzas.

7. Combo audio (pre-bake silence-in-blanked-slot mp3s per block)
   python songs/_pipeline/combo_audio.py \
     --blocks songs/<slug>/blocks.yaml \
     --media-dir songs/<slug>/media \
     --prefix <slug> \
     --ffmpeg <ffmpeg-bin> --ffprobe <ffprobe-bin>

8. English glosses (manual)
   ◇◇◇ REVIEW CHECKPOINT #2 — English ◇◇◇

   - Write one English line per Hanzi line in
     songs/<slug>/english.txt — the line count MUST equal the count in
     aligned.json (including duplicate lines; the duplicates are skipped
     at TSV build time but the file is read positionally).
   - Use rough conversational translations, not literal word-by-word.
     The Breakdown column already covers per-char meaning. The English
     line is the "what does this stanza say?" gloss.
   - Match the song's register: ballads → faithful, pop → idiomatic,
     classical → tolerate stiffness.

9. Emit TSVs (Lines split into Basic + Cloze; Blocks separate)
   python songs/_pipeline/build_tsv.py \
     --aligned     songs/<slug>/aligned.json \
     --english     songs/<slug>/english.txt \
     --breakdown   songs/<slug>/breakdown.txt \
     --cloze-plan  songs/<slug>/cloze_plan.yaml \
     --out-stem    songs/<slug>/Chinese_Song_<Title>_Lines \
     --prefix <slug> --song-slug <slug> \
     --tag song --tag song-<slug> --tag artist-<slug>

   python songs/_pipeline/build_blocks_tsv.py \
     --blocks      songs/<slug>/blocks.yaml \
     --aligned     songs/<slug>/aligned.json \
     --english     songs/<slug>/english.txt \
     --breakdown   songs/<slug>/breakdown.txt \
     --out         songs/<slug>/Chinese_Song_<Title>_Blocks.tsv \
     --prefix <slug> --song-slug <slug> \
     --tag song --tag song-<slug> --tag artist-<slug>

10. Cleanup unused media
    python songs/_pipeline/cleanup_media.py \
      --media-dir songs/<slug>/media \
      --prefix <slug> \
      --blocks songs/<slug>/blocks.yaml \
      --line-tsv songs/<slug>/Chinese_Song_<Title>_Lines_Cloze.tsv

    Removes line clips for skipped duplicate lines + orphan combo files
    from deduped blocks. Always run as the last step.

11. CrowdAnki deck.json (one-click import format, layered on the TSVs)
    python songs/_pipeline/build_crowdanki.py --song-dir songs/<slug>

    Reads the 3 TSVs + note-type templates + media/, writes
    songs/<slug>/deck.json and drops _ruby.js + _song_ruby.js into
    media/ so a CrowdAnki "Import from folder" installs everything (note
    types, cards, audio, JS) in one step — no manual collection.media
    copy, no template paste. Deck name defaults to
    Chinese::Songs::<title_zh>; override with --deck-name. Stable UUIDs →
    re-import UPDATES instead of duplicating. The 3 note-type names are
    global constants (MODELS) in the script — edit there if the user
    renamed their note types. TSVs stay; this is an additional format.

12. Commit
    git add songs/<slug>/ <any pipeline tweaks>
    git commit -m "feat(songs): add <Title> (<Artist>)"

    Don't forget to add new CHAR_OVERRIDES from step 4 to the commit if
    you extended them — those benefit all future songs.
```

## After the pipeline — user-facing instructions

End the run with a summary aimed at the user actually opening Anki.
Two import routes — CrowdAnki is the one-click path:

**A. CrowdAnki (recommended — one click, auto-installs everything):**
1. Install the CrowdAnki add-on if not already present.
2. File → CrowdAnki: Import from folder → pick `songs/<slug>/`. This
   creates the deck (`Chinese::Songs::<title>`), the 3 note types, all
   notes, the audio, and the template JS in one step. Re-importing
   updates in place (stable GUIDs) — no duplicates.

**B. Manual TSV (if not using CrowdAnki):**
1. Copy `songs/<slug>/media/*.mp3` into Anki's `collection.media/`.
2. Import the three TSVs in order — Cloze, Block, Basic — each into
   its matching note type. Sequence matters for deck-wide new-card
   order (cloze cards introduced first, reading cards last).
3. The three note types are set up once per Anki profile; see
   `songs/_note_types/README.md` for the field lists + template HTML.

## Embedded English (code-switched lyrics)

Some tracks sing English *as part of a line* — a stray "HELLO", or whole
English hooks in Mandarin rap. That **lexical** English (it's sung) is
distinct from **translation** English (a gloss the lyric site added).
Strip translations and non-lexical ad-libs; **keep lexical English
inline.**

Safe to keep inline — verified against the templates:

- `build_tsv.line_pinyin` uses pypinyin `errors="ignore"` → exactly one
  syllable **per Han char**; English contributes no token.
- `_ruby.js` (`buildRuby`) and `_song_ruby.js` (`countHan`) compare the
  pinyin-token count to the **Han-char count only**, render `<rt>` pinyin
  over Han chars, and pass non-Han through as plain inline text. So
  interspersed English never desyncs the ruby — it just sits inline with
  no pinyin above it.

What the helpers *don't* do for English (degraded, not broken):

- `gloss.py` skips non-Han, so English words get **no Breakdown entry** —
  hand-edit `breakdown.txt` if a hook word deserves a gloss.
- `cloze_pick.py` (jieba) tags English `x` and never suggests it, but
  `inject_clozes` is a raw substring replace, so you can hand-add a
  load-bearing English word to `selected_clozes` and `{{cN::word}}` works.

If a heavily code-switched track aligns poorly under the forced
`language="zh"`, retry `align.py` with `--model medium`.

## What to escalate vs handle silently

| Situation | Action |
|-----------|--------|
| Alignment looks visibly broken | Stop. Show user the bad rows, propose retry with `--model medium`. |
| jieba mis-segments reduplication | Auto-fix at review checkpoint #1; user just nods. |
| User-provided English is short | Auto-write English in the user's voice from the lyrics + the polished translation if they pasted one; show before-emit. |
| Spoken-word interlude is one long line | Suggest splitting; do it via lyrics_simplified.txt edit + re-align. |
| Block all-chorus | Already auto-handled by block_plan.py dedup. |
| Audio file fails ffmpeg extraction | Fall back to manual `ffmpeg -i webm mp3`. Mention to user. |
| Lyrics paste has explanatory English / translation lines interspersed | Strip silently; show what was stripped only if it's >5 lines. |
| Lexical English sung *inside* a line (HELLO, rap hooks) | Keep inline — don't strip. Render handles it (pinyin only over Han). See "Embedded English". |
| User asks "is this gloss right?" mid-pipeline | Treat as a normal question — don't break flow unless they want to abort. |

## Things to NOT do

- Don't try to mash this into the word-deck schema. Songs are a
  separate world (different note types, different TSVs, different
  scope guardrails). See `songs/README.md`.
- Don't auto-translate English glosses with a non-Claude path. The
  user has been treating these as a personal-flavor field.
- Don't strip lexical (sung) English from a line — a "HELLO", an English
  rap hook — keep it inline. Only translation/ad-lib English is stripped.
  See "Embedded English".
- Don't skip cleanup_media.py. The duplicate clips waste ~30-40% of
  the song dir's storage on chorus-heavy tracks.
- Don't generate per-song note types. There are three shared note
  types (SongLineBasic, SongLineCloze, SongBlock) and every song
  uses the same three.
- Don't commit `audio.webm` or `audio.mp3` (gitignored). Per-line
  clips and combos are tracked; full song audio is regenerable.
