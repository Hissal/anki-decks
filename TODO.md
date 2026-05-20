# TODO / future ideas

Project-wide working list of ideas, deferred work, and "would be nice"
improvements that aren't worth blocking current work on. Separate from
`FUTURE_DECKS.md`, which is specifically scoped to candidate new decks.

Each entry is an idea, not a commitment. Add freely; promote to a real
plan / branch when one becomes worth doing.

---

## Word-deck card structure

### Tag-gated audio-only card (4th card type)

Default word-deck note type stays at 3 cards (intro / hanzi recognition /
production). An optional 4th card type — pure audio recognition, hanzi
hidden behind a reveal button — should emit only when a row carries an
opt-in tag like `listening-drill`.

Why opt-in rather than always-on: TTS reliability is uneven and the
generic audio-recognition card was retired for exactly that reason (see
`note_type/Chinese_anki_decks/archive/`). For homophones, tone-confusable
pairs, and short high-frequency function words where listening drill is
genuinely worth the TTS risk, a tagged subset of cards earns its keep.

Implementation sketch:

- Card template wrapped in an Anki conditional: `{{#tag:listening-drill}}…{{/tag:listening-drill}}`
  (or, more robustly, check via JS for the tag in `{{Tags}}` and bail
  out of mounting if absent — Anki's `{{#tag:…}}` is not a standard
  field-conditional and would need verification).
- Front: HTML5 audio autoplay, "Show Hanzi" reveal button, no English.
- Back: full reveal (mirror the other three backs).
- Hint card-type prefix: `audio:` is already reserved in `HINT_CARD_TYPES`
  for exactly this purpose — no schema change needed.
- Archive templates at `note_type/Chinese_anki_decks/archive/` are
  recoverable starting points; would need the conditional wrapper added.

Acceptance: cards only generate for rows with the tag set; rows without
the tag produce the standard 3 cards.

### Strip the manual Play Audio button from `hanzi_recognition_front.html`

The read-only Card 2 currently has a manual Play Audio button. That
button is useful as a fallback when the user genuinely can't read a
character, but it also lets you cheat on the reading drill. A purer
variant would remove it entirely so the card is silent until the back
flips.

Trade-off: harder when stuck, but more honest test of reading. Could
also be opt-in via a per-row tag (e.g. `strict-reading`) — similar
plumbing to the tag-gated audio-only card above.

### Audit existing Hint values for retired `audio:` prefix usage

Some rows' `Hint` field may carry lines scoped to `audio:` from when the
deck had a dedicated audio-recognition card. With that card retired,
those hints no longer render anywhere by default. Either:

- Re-route relevant hints to `intro:` (audio-supplemented intro card).
- Leave them as-is for the future tag-gated audio card (still valid
  prefix).

Bulk audit: `grep '\baudio\s*:' Chinese_*.tsv` should surface candidates.
