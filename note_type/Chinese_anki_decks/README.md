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
| `audio_recognition_front.html` | Card 2 front — custom HTML5 audio mount autoplays at the configured volume, `Show Hanzi` hint reveals ruby with pinyin hidden. |
| `audio_recognition_back.html`  | Card 2 back — full reveal. |
| `production_front.html`        | Card 3 front — English only. |
| `production_back.html`         | Card 3 back — full reveal. |
| `styles.css`                   | Shared styling — paste into the note type's "Styling" pane. |
| `_ruby.js`                     | Ruby builder + toggle + examples renderer + HTML5 audio helpers. Goes in `collection.media`. |
| `addon/`                       | Anki add-on. Registers `{{soundfile:Audio}}` / `{{nosound:Audio}}` template filters, plus a 🔊 volume button in the top toolbar that controls audio playback level across all cards. |

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

5. **Install the add-on.** Anki's autoplay scanner triggers on *any*
   `[sound:filename.mp3]` token in the rendered HTML — even inside `hidden`
   divs or `data-` attributes. And we want a single volume slider that
   controls every card's audio. The add-on solves both:

   - Registers two template filters:
     - `{{soundfile:Audio}}` — returns just `foo.mp3` (no `[sound:…]` wrapper,
       so Anki's autoplay scanner finds nothing to play). Templates pass this
       filename to an HTML5 `<audio>` element instead.
     - `{{nosound:Audio}}` — returns the field text with every `[sound:…]`
       reference stripped (kept for future use; not currently needed by the
       templates).
   - Adds a 🔊 button to Anki's main top toolbar. Click to open a slider
     (0–100%). The chosen value is persisted in the add-on's config and
     injected into every reviewer page render as
     `window.ankiDecksConfig.volume`. `_ruby.js` reads it when constructing
     audio elements, so changes apply from the next card render onward.

   Install:
   - Locate your Anki add-ons folder:
     - Windows: `%APPDATA%\Anki2\addons21\`
     - macOS: `~/Library/Application Support/Anki2/addons21/`
     - Linux: `~/.local/share/Anki2/addons21/`
   - Copy the `addon/` directory from this repo into `addons21/` and rename
     it (e.g. to `chinese_anki_decks`).
   - Restart Anki. The filters are now available in any template and the 🔊
     button appears in the top toolbar.

   Configuration lives in the add-on's `config.json` (`volume`, integer
   0–100, default 70) and is also editable via `Tools → Add-ons → Config`.

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

### Audio playback

All four sides that play audio (cards 1/2/3 backs and card 2 front) route
through `mountAutoplayAudio` in `_ruby.js`: the template renders
`<div class="audio-mount" data-soundfile="{{soundfile:Audio}}"></div>`, the
script reads the filename, constructs an HTML5 `<audio>` element at the
configured volume, autoplays it, and adds a replay button. Card 1 front's
Play Audio button uses the same volume-aware helper.

No `[sound:…]` token is ever rendered to the DOM, so Anki's native autoplay
scanner is fully bypassed. The R key still replays the most recently
autoplayed audio (bound by `_ruby.js`).
