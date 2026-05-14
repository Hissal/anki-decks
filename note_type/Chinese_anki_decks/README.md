# Chinese (anki-decks) — note type

Custom Anki note type for the three TSV decks in this repo. Ruby pinyin above
each hanzi (hidden by default, hover/tap/toggle to reveal), three card modes
covering audio recognition, hanzi recognition, and production, and a
`PersonalNote` field that survives TSV re-imports.

## Files

| File | Purpose |
|------|---------|
| `audio_recognition_front.html` | Card 1 front — `{{Audio}}` autoplays, `Show Hanzi` hint reveals ruby with pinyin hidden. |
| `audio_recognition_back.html`  | Card 1 back — full reveal. |
| `hanzi_recognition_front.html` | Card 2 front — ruby with pinyin hidden, `{{hint:Audio}}` plays audio on click. |
| `hanzi_recognition_back.html`  | Card 2 back — full reveal. |
| `production_front.html`        | Card 3 front — English only. |
| `production_back.html`         | Card 3 back — full reveal. |
| `styles.css`                   | Shared styling — paste into the note type's "Styling" pane. |
| `_ruby.js`                     | Ruby builder + toggle + examples renderer. Goes in `collection.media`. |

## One-time install

1. **Create the note type.** In Anki: `Tools → Manage Note Types → Add →
   Add: Basic`, name it `Chinese (anki-decks)`. Click `Fields…` and add
   fields in this order, deleting `Front`/`Back`:
   ```
   Hanzi
   Pinyin
   English
   Breakdown
   Examples
   Note
   Link
   PersonalNote
   Audio
   ```
   Set `Hanzi` as the sort field.

2. **Add the three card templates.** `Manage Note Types → Cards`. Rename the
   default card to `1 Audio recognition`, then `Add Card Type` twice for
   `2 Hanzi recognition` and `3 Production`. Paste the corresponding
   `*_front.html` and `*_back.html` files into the front/back templates.

3. **Paste styling.** Paste `styles.css` into the shared "Styling" pane.

4. **Install the ruby script.** Copy `_ruby.js` into your Anki profile's
   `collection.media` folder (Windows: `%APPDATA%\Anki2\<profile>\collection.media\`,
   macOS: `~/Library/Application Support/Anki2/<profile>/collection.media/`,
   Linux: `~/.local/share/Anki2/<profile>/collection.media/`). The leading
   underscore tells Anki not to clean it up as unused media.

5. **Disable autoplay on card 2 front (optional but recommended).** Anki
   autoplays `[sound:…]` references on whichever side renders them. Card 2
   front omits `{{Audio}}` from its HTML — only the `{{hint:Audio}}` element
   appears — so autoplay is already suppressed in practice. If your Anki
   build still autoplays through the hint, toggle off
   `Deck options → Audio → Don't play audio automatically`.

## How the templates work

### Ruby alignment

The Pinyin field stores one syllable per CJK character (space-separated). At
render time, `_ruby.js` reads `data-hanzi` and `data-pinyin` from the
`.hanzi-block` element, walks through the hanzi character-by-character, and
emits one `<ruby>` per CJK char. Non-CJK characters (punctuation, ASCII)
render as plain text and don't consume a pinyin token. If the token count
doesn't match the CJK char count, it logs a warning and falls back to bare
text — the repo's validator enforces this invariant so it shouldn't happen
in practice.

### Pinyin visibility

| State | Pinyin |
|-------|--------|
| Default front of card 2 | All hidden. |
| Hover one character (desktop) | That character's pinyin appears. |
| Tap one character | Toggle `.revealed` on that `<ruby>` — works on mobile and desktop. |
| Click `Toggle Pinyin` | Toggle `.show-all-ruby` on the container — every pinyin shows or hides. |
| All backs | Mounted with `.show-all-ruby` already on — full reveal by default. |

### Examples rendering

The `Examples` field stores 1–3 sentences separated by literal `<br>`. Each
sentence has the form `中文。 / English.` On the back, `_ruby.js` splits the
field into a styled `<ul>` with one `<li>` per sentence, Chinese on top and
italic English below.

### Field-level conditionals

Every optional section is wrapped in `{{#FieldName}}…{{/FieldName}}` so
empty `Breakdown` / `Examples` / `Note` / `Link` / `PersonalNote` collapse
cleanly with no orphan headers.
