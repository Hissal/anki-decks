# SongLineCloze note type

Anki **Cloze** note type. Generates one card per `{{cN::word}}` marker in the `Hanzi` field — each card hides one word and asks you to recall it from line context.

Pairs with [SongLineBasic](SongLineBasic.md) (Reading + Recall-line cards).

## Front design rationale

- **No audio on the front.** Hearing the line would leak the blanked word.
- **No pinyin on the front, even on hover.** The pinyin field is whole-line; hovering revealed pinyin would tell you the blanked word's syllable. We keep the front to plain hanzi with one slot blanked.
- The Anki cloze renderer wraps the blanked content in `<span class="cloze">[…]</span>`, which the shared CSS styles in a red accent.

The back side shows the full line with ruby pinyin (hover-reveal) + audio autoplays + English + Breakdown — same affordances as the Reading card.

## Why two `{{cloze:Hanzi}}` on the back

Anki's Cloze note type **requires** the cloze field to appear on both the front and back templates. `{{FrontSide}}` alone on the back is not enough — Anki rejects the template with "Cloze placeholder missing from the back side". So the back includes `{{cloze:Hanzi}}` again, this time wrapped as a ruby block (so the revealed answer also gets per-char pinyin via hover).

## Fields (8)

Set the note type's base type to **Cloze** when creating it. Then customize fields:

| # | Field name | Notes |
|---|------------|-------|
| 1 | `Key` | sort field — same key as the SongLineBasic note |
| 2 | `SongSlug` | |
| 3 | `LineNo` | |
| 4 | `Hanzi` | line text **with** `{{c1::word}}` markers |
| 5 | `Pinyin` | |
| 6 | `English` | |
| 7 | `Breakdown` | |
| 8 | `Audio` | |

In note-type editor → **Cards**, set the **Sort field** to `Key`.

## Card — Cloze

**Front template:**

```html
<div class="meta">{{SongSlug}} · line {{LineNo}} · cloze</div>

<div class="hanzi-block">{{cloze:Hanzi}}</div>
```

The front renders the line with one cloze blanked as `[…]`. No `id` / `data-*` attributes — we deliberately skip the ruby JS on the front so no pinyin can leak.

**Back template:**

(No `{{FrontSide}}` — Anki doesn't replay the audio when the front is re-included that way. The audio is included directly on the back so it plays on flip. Only one `{{cloze:Hanzi}}` on the back — that's what Anki requires for the template to validate, and it's already inside the ruby mount so pinyin renders on top of the revealed line.)

```html
<div class="meta">{{SongSlug}} · line {{LineNo}} · cloze</div>

<div class="audio">{{Audio}}</div>

<div class="hanzi-block show-all-ruby"
     id="songcloze-back-hanzi"
     data-pinyin="{{text:Pinyin}}">{{cloze:Hanzi}}</div>

<hr>

<div class="english">{{English}}</div>
<div class="breakdown">{{Breakdown}}</div>

<script src="_ruby.js"></script>
<script src="_song_ruby.js"></script>
<script>
  // Anki's back-side cloze render reveals all clozes, so .textContent
  // matches the Pinyin field syllable count. .show-all-ruby on the
  // container makes all rt visible by default.
  window.songsRuby.mountElement("songcloze-back-hanzi");
</script>
```

## Styling

Paste the contents of [styling.css](styling.css) into the note type's **Styling** tab.

## Dependencies

- `_ruby.js` from the word-deck setup, in Anki's `collection.media/`
- `_song_ruby.js` (see [README.md](README.md) for the one-time install) — same dir

## Import

```
File → Import → pick Chinese_Song_<X>_Lines_Cloze.tsv
  Note type: SongLineCloze
  Update existing notes when first field matches: ON
```
