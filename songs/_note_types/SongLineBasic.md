# SongLineBasic note type

Standard (non-cloze) Anki note type. Hosts two card templates per line:

1. **Recall-line** — previous line's audio + Hanzi → recall this line. For line 1 (no previous line) the front falls back to a "first line of the song?" prompt.
2. **Reading** — audio + Hanzi as ruby → recall English meaning.

The template order matters: **Recall is Card 1, Reading is Card 2**. Anki picks new cards by (note position, then card-template index), so swapping these gives the desired Recall-before-Reading flow when the Basic TSV is imported.

Pairs with [SongLineCloze](SongLineCloze.md) (cloze cards) and [SongBlock](SongBlock.md) (block cloze cards).

## Dependency: `_ruby.js` in Anki's collection.media

The word-deck templates ship a shared JS helper (`note_type/Chinese_anki_decks/_ruby.js`) that builds `<ruby><rt>` markup from `data-hanzi` + `data-pinyin` attributes. Song templates reuse it. Make sure `_ruby.js` is in your Anki profile's `collection.media/` directory — it's there already if you've used the word decks.

## Fields (10)

| # | Field name | Notes |
|---|------------|-------|
| 1 | `Key` | sort field — `<song_slug>_<NNN>`. Match-on-import key. |
| 2 | `SongSlug` | |
| 3 | `LineNo` | |
| 4 | `HanziPlain` | line text, no cloze markers |
| 5 | `Pinyin` | tone-marked, one syllable per CJK char, space-separated |
| 6 | `English` | rough gloss for whole line |
| 7 | `Breakdown` | `char (gloss) char (gloss) …` |
| 8 | `Audio` | `[sound:<slug>_<NNN>.mp3]` |
| 9 | `PrevHanzi` | line N-1's plain text (empty for line 1) |
| 10 | `PrevAudio` | line N-1's `[sound:…]` ref (empty for line 1) |

In note-type editor → **Cards**, set the **Sort field** to `Key`.

## Card 1 — Recall-line

The card generates for every line. For lines 2+, the front shows the previous line's audio + Hanzi and prompts for the next line. For line 1 (PrevHanzi empty), the front falls back to a "first line of the song?" prompt.

**Front template:**

```html
{{#PrevHanzi}}
<div class="meta">{{SongSlug}} · what's the next line?</div>

<div class="audio">{{PrevAudio}}</div>

<div class="hanzi-block prev">{{PrevHanzi}}</div>

<div class="prompt">→ what comes next?</div>
{{/PrevHanzi}}

{{^PrevHanzi}}
<div class="meta">{{SongSlug}} · first line</div>

<div class="prompt">→ how does the song start?</div>
{{/PrevHanzi}}
```

**Back template:**

(No `{{FrontSide}}` — Anki doesn't re-trigger the underlying audio's autoplay when the front is re-included that way. Audio is inlined fresh on the back so `{{Audio}}` plays on flip. `PrevAudio` is **not** included on the back so the line you're learning is the only audio that plays.)

```html
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
</script>
```

## Card 2 — Reading

Audio autoplays on the front. Hanzi shows large; pinyin only appears when you hover over a character (or tap on mobile). Toggle button reveals all at once.

**Front template:**

```html
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
</script>
```

**Back template:**

```html
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
</script>
```

## Styling

Paste the contents of [styling.css](styling.css) into the note type's **Styling** tab.

## Import

```
File → Import → pick Chinese_Song_<X>_Lines_Basic.tsv
  Note type: SongLineBasic
  Deck:      one deck per song, e.g. Chinese::Songs::一剪梅
  Update existing notes when first field matches: ON
```

Import Basic **last** (after Cloze and Block TSVs) so its notes get higher positions — that puts Recall/Reading cards after Cloze/Block cards in the deck's new-card queue.
