# Chinese (anki-decks) — note type

Custom Anki note type for the three TSV decks in this repo. Ruby pinyin above
each hanzi (hidden by default, hover/tap/toggle to reveal), three card modes
covering hanzi recognition, audio recognition, and production, and a
`PersonalNote` field that survives TSV re-imports.

Card order matches the order in which Anki introduces new cards from a note:
hanzi recognition first (most beginner-friendly), audio recognition second,
production last.

## Files

| File | Purpose |
|------|---------|
| `hanzi_recognition_front.html` | Card 1 front — ruby with pinyin hidden, custom `Play Audio` button parses `{{soundfile:Audio}}` and plays via HTML5 audio without triggering Anki's autoplay. |
| `hanzi_recognition_back.html`  | Card 1 back — full reveal. |
| `audio_recognition_front.html` | Card 2 front — `{{Audio}}` autoplays, `Show Hanzi` hint reveals ruby with pinyin hidden. |
| `audio_recognition_back.html`  | Card 2 back — full reveal. |
| `production_front.html`        | Card 3 front — English only. |
| `production_back.html`         | Card 3 back — full reveal. |
| `styles.css`                   | Shared styling — paste into the note type's "Styling" pane. |
| `_ruby.js`                     | Ruby builder + toggle + examples renderer. Goes in `collection.media`. |
| `addon/`                       | Anki add-on registering the `{{soundfile:Audio}}` template filter. Required for card 2 front's Play Audio button to work without triggering autoplay. |

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
   default card to `1 Hanzi recognition`, then `Add Card Type` twice for
   `2 Audio recognition` and `3 Production`. Paste the corresponding
   `*_front.html` and `*_back.html` files into the front/back templates.
   The order matters — Anki introduces new cards in template order, and the
   hanzi-recognition card is the most beginner-friendly entry point.

3. **Paste styling.** Paste `styles.css` into the shared "Styling" pane.

4. **Install the ruby script.** Copy `_ruby.js` into your Anki profile's
   `collection.media` folder (Windows: `%APPDATA%\Anki2\<profile>\collection.media\`,
   macOS: `~/Library/Application Support/Anki2/<profile>/collection.media/`,
   Linux: `~/.local/share/Anki2/<profile>/collection.media/`). The leading
   underscore tells Anki not to clean it up as unused media.

5. **Install the nosound filter add-on.** Anki's autoplay scanner
   triggers on *any* `[sound:filename.mp3]` token in the rendered HTML —
   even inside `hidden` divs or `data-` attributes. To keep card 1's front
   from autoplaying while still letting cards 2 and 3 autoplay normally,
   the `Play Audio` button reads the audio filename via a custom template
   filter `{{soundfile:Audio}}` that returns just `foo.mp3` (no `[sound:…]`
   wrapper). Install:

   - Locate your Anki add-ons folder:
     - Windows: `%APPDATA%\Anki2\addons21\`
     - macOS: `~/Library/Application Support/Anki2/addons21/`
     - Linux: `~/.local/share/Anki2/addons21/`
   - Copy the `addon/` directory from this repo into `addons21/` and rename
     it to `chinese_anki_decks_nosound` (or any folder name — Anki uses the
     folder name as the package id).
   - Restart Anki. The filter is now available in any note type's templates.

   The add-on is ~25 lines of Python (`addon/__init__.py`). It registers
   two filters:
   - `{{soundfile:Audio}}` — returns `foo.mp3`
   - `{{nosound:Audio}}` — returns the field text with every `[sound:…]`
     reference stripped (useful if you mix sound refs with other content).

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
| Default front of card 1 (Hanzi recognition) | All hidden. |
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
