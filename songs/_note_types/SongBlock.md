# SongBlock note type

Anki **Cloze** note type. One note per N-line block. Each line in the block is wrapped in its own `{{cN::line}}` marker, so the note generates one card per line — each card hides ONE whole line while showing the others.

The `BlockAudio` field uses the same cloze grouping: each `{{cN::[sound:…]}}` wraps a pre-baked combo mp3 (lines around the blanked slot + silence in the slot). Anki only renders the active cloze's contents, so each card plays exactly the combo that matches its blanked line — keeping the song's rhythm intact while the listener tries to recall the missing line.

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
| 8 | `BlockAudio` | `{{c1::[sound:…_c1.mp3]}}{{c2::[sound:…_c2.mp3]}}…` |

In note-type editor → **Cards**, set the **Sort field** to `Key`.

## Card — Block cloze

The combo audio autoplays. The four lines render with one slot as `[…]` (the active cloze). Ruby pinyin is built per-line via `_song_ruby.js`; hover a character to see its pinyin.

**Front template:**

```html
<div class="meta">{{SongSlug}} · block {{BlockNo}}</div>

<div class="audio">{{cloze:BlockAudio}}</div>

<div class="lines-block"
     id="songblock-lines"
     data-pinyin="{{text:Pinyin}}">{{cloze:Lines}}</div>

<button class="toggle-btn" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

<script src="_ruby.js"></script>
<script src="_song_ruby.js"></script>
<script>
  window.songsRuby.mountLines("songblock-lines");
  window.ankiDecks.attachToggle("songblock-lines", "toggle-pinyin-btn");
</script>
```

`{{cloze:Lines}}` returns the four lines separated by `<br>`, one of them wrapped as `<span class="cloze">[…]</span>`. `_song_ruby.js` walks each `<br>`-separated chunk, pairs it with the matching pinyin line, and replaces each plain-text line with a `<ruby>` markup. The clozed line (`[…]`) is left alone — no ruby on the blank.

**Back template:**

(No `{{FrontSide}}`. Audio re-included so it plays on flip; pinyin auto-revealed via `.show-all-ruby`.)

```html
<div class="meta">{{SongSlug}} · block {{BlockNo}}</div>

<div class="audio">{{cloze:BlockAudio}}</div>

<div class="lines-block show-all-ruby"
     id="songblock-lines-back"
     data-pinyin="{{text:Pinyin}}">{{cloze:Lines}}</div>

<hr>

<div class="english">{{English}}</div>
<div class="breakdown">{{Breakdown}}</div>

<script src="_ruby.js"></script>
<script src="_song_ruby.js"></script>
<script>
  window.songsRuby.mountLines("songblock-lines-back");
</script>
```

## Styling

Paste the contents of [styling.css](styling.css) into the note type's **Styling** tab.

## Dependencies

- `_ruby.js` from the word-deck setup, in Anki's `collection.media/`
- `_song_ruby.js` (see [README.md](README.md) for one-time install)

## Import

```
File → Import → pick Chinese_Song_<X>_Blocks.tsv
  Note type: SongBlock
  Update existing notes when first field matches: ON
```
