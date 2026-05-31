# SongBlock note type

Anki **Cloze** note type. One note per N-line block. Each line in the block is wrapped in its own `{{cN::line}}` marker, so the note generates one card per line — each card hides ONE whole line while showing the others.

**All audio routes through `_ruby.js::mountAutoplayAudio`** — the same volume-aware HTML5-audio helper the word decks use, so the 🔊 volume addon (`window.ankiDecksConfig.volume`) controls it. Never use native `[sound:]`: native autoplay bypasses that knob. Both sides pass `{controls:true}` so the long block clips get native **play/pause + a seek timeline**. Only one clip plays at a time — starting a clip (and page-hide) stops the previous one, so audio never bleeds across the flip or into the next card.

- **Front — silenced-slot combo, picked by JS.** Anki cloze rendering blanks the *active* cloze and *reveals* every sibling, so a `{{cN::[sound:…]}}` grouping would play the three combos you DON'T want and mute the one you do (the exact opposite of recall). Instead the front template runs `playBlockAudio` (in `_song_ruby.js`): it detects which line slot is the active cloze, computes that slot's pre-baked combo (`<slug>_block_<NN>_c<K>.mp3` — the block with line K silenced) from `SongSlug` + `BlockNo` + the detected slot, sets it as `data-soundfile`, and hands off to `mountAutoplayAudio`. The gap lets the listener try to recall the missing line.
- **Back — full block.** Plays `<slug>_block_<NN>_full.mp3` (no silence) so the answer line is audible. Same file for all 4 cards → no per-card selection, so it's a plain `{{soundfile:BlockAudio}}` mount handed to `mountAutoplayAudio`, exactly like a word-deck back card.

## Fields (8)

Set the note type's base type to **Cloze**.

| # | Field name | Notes |
|---|------------|-------|
| 1 | `Key` | `<song_slug>_block_<NN>` |
| 2 | `SongSlug` | |
| 3 | `BlockNo` | |
| 4 | `Lines` | `{{c1::line_1}}<br>{{c2::line_2}}<br>…` — the cloze field |
| 5 | `Pinyin` | per-line pinyin, joined with `<br>` |
| 6 | `English` | per-line English, joined with `<br>` |
| 7 | `Breakdown` | merged across the block |
| 8 | `BlockAudio` | Full-block ref for the **back**: `[sound:<slug>_block_<NN>_full.mp3]`. Consumed via `{{soundfile:BlockAudio}}` (the filter strips the `[sound:…]` wrapper) → `mountAutoplayAudio`. Front audio is JS-selected per-card (not from a field). |

In note-type editor → **Cards**, set the **Sort field** to `Key`.

## Card — Block cloze

The combo audio autoplays. The four lines render with one slot as `[…]` (the active cloze). Ruby pinyin is built per-line via `_song_ruby.js`; hover a character to see its pinyin.

**Front template:**

```html
<div class="meta">{{SongSlug}} · block {{BlockNo}}</div>

<div class="audio-mount" id="songblock-audio"></div>

<div class="lines-block"
     id="songblock-lines"
     data-pinyin="{{text:Pinyin}}">{{cloze:Lines}}</div>

<button class="toggle-btn" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

<script src="_ruby.js"></script>
<script src="_song_ruby.js"></script>
<script>
  // Detect the blanked slot and play only that slot's combo (via the shared
  // volume-aware mountAutoplayAudio). Must run BEFORE mountLines, which
  // rewrites the lines container's innerHTML.
  window.songsRuby.playBlockAudio("songblock-lines", "songblock-audio", "{{SongSlug}}", "{{BlockNo}}");
  window.songsRuby.mountLines("songblock-lines");
  window.ankiDecks.attachToggle("songblock-lines", "toggle-pinyin-btn");
</script>
```

`{{cloze:Lines}}` returns the four lines separated by `<br>`, one of them wrapped as `<span class="cloze">[…]</span>`. `_song_ruby.js` walks each `<br>`-separated chunk, pairs it with the matching pinyin line, and replaces each plain-text line with a `<ruby>` markup. The clozed line (`[…]`) is left alone — no ruby on the blank.

**Back template:**

(No `{{FrontSide}}`. Audio re-included so it plays on flip; pinyin auto-revealed via `.show-all-ruby`.)

The back plays the FULL block (no silenced slot) so the answer line is
audible. Same file for all 4 cards → no per-card selection, so it's a plain
`{{soundfile:BlockAudio}}` mount handed to `mountAutoplayAudio` (the same
volume-aware helper the front and the word decks use).

```html
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
</script>
```

## Styling

Paste the contents of [styling.css](styling.css) into the note type's **Styling** tab.

## Dependencies

- `_ruby.js` from the word-deck setup, in Anki's `collection.media/` — provides `mountAutoplayAudio` (volume-aware HTML5 audio).
- `_song_ruby.js` (see [README.md](README.md) for one-time install)
- The **chinese_anki_decks add-on** (same one the word decks need): registers the `{{soundfile:…}}` filter and injects the 🔊 volume knob (`window.ankiDecksConfig.volume`) that both front and back audio honor. Without it, `{{soundfile:BlockAudio}}` is inert and audio falls back to a default volume.

## Import

```
File → Import → pick Chinese_Song_<X>_Blocks.tsv
  Note type: SongBlock
  Update existing notes when first field matches: ON
```
