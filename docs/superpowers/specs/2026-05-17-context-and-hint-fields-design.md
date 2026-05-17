# Design: `Context` + `Hint` fields for word-deck note type

## Background

The three word decks (`Chinese_Core_Conversation.tsv`, `Chinese_Idioms_Proverbs_Classical.tsv`, `Chinese_Slang_Dialect_Flavor.tsv`) share an 8-column schema and one Anki note type (`note_type/Chinese_anki_decks/`). The Production card (Card 3) presents only the `English` field on its front — the user must produce the Hanzi from English alone.

This works for unambiguous entries, but breaks down for slang and idioms where the English gloss has many valid Mandarin translations. Example: `杠杠的` glosses as "awesome / excellent" — but so do `牛逼`, `酷毙了`, `666`, `给力`. With only "awesome" on the prompt, the production card teaches the **card** (recognize this Anki note) rather than the **word** (produce this specific term in its register). The user picks the right answer by elimination instead of by recall.

A separate, related want: an optional click-to-reveal **hint** available on any card type, providing a clue (mnemonic / starting char / shape cue) when the user is stuck.

## Goal

Add two new optional fields to the word-deck schema and note type:

- **`Context`** — terse disambiguator (register / region / scenario). Always-visible on the production front and on all 3 backs. Without it, the production prompt is genuinely ambiguous.
- **`Hint`** — click-to-reveal help available on all 3 fronts; auto-revealed on all 3 backs. Format supports per-card-type variants while keeping the simple "same hint everywhere" case trivial.

Both fields are intrinsic word data, versioned in the TSV alongside `Hanzi` / `English` / `Note`.

Non-goals:

- Migrating existing `Note` content into `Context` automatically. Some Notes carry register info ("Northeastern-flavored slang.") that would be perfect Context, but auto-extraction is fragile. Done by hand row-by-row, or in a separate batch task later.
- Applying these fields to the components / radicals decks. Those have their own note types and schemas; this design is word-decks-only.

## Schema bump (8 → 10 cols)

Directive block in all three word-deck TSVs becomes:

```
#separator:tab
#html:true
#columns:Hanzi	Pinyin	English	Breakdown	Examples	Note	Context	Hint	Link	Tags
#tags column:10
```

| # | Column | New? |
|---|---|---|
| 1 | Hanzi | — |
| 2 | Pinyin | — |
| 3 | English | — |
| 4 | Breakdown | — |
| 5 | Examples | — |
| 6 | Note | — |
| 7 | **Context** | new |
| 8 | **Hint** | new |
| 9 | Link | — |
| 10 | Tags | — |

`Context` + `Hint` sit between `Note` and `Link` because they are the closest semantic neighbors to `Note` (free-form per-card annotations). Anki imports by the `#columns:` directive, so column position only matters for human readability — Anki uses the named mapping.

### Field semantics

| Field | Purpose | Length guidance |
|---|---|---|
| `Context` | Disambiguator so the production prompt is answerable without seeing the back. Examples: `northeastern slang`, `Sichuan dialect`, `internet shorthand`, `formal/written`. | Terse — register / region / scenario tag. ~3–8 words. |
| `Hint` | Optional clue to assist recall on any card type. Examples: `starts with 杠`, `doubled syllable + 的`, `food metaphor`. | Short — under one rendered line per part. Multi-line allowed via per-card prefixes (below). |

Both fields are optional. Existing rows simply leave them empty.

## Hint formatting (per-card-type variants)

`<br>`-separated lines (matches `Examples` convention; `#html:true` is already set on the deck files). Each line is either universal (no prefix) or card-type-specific (prefix). Format:

```
[card-type:] hint text<br>[card-type:] hint text<br>...
```

where `card-type` ∈ `{hanzi, audio, production}`, case-insensitive, optional whitespace after the colon. Anything else before a colon is treated as content (the line counts as universal).

**Parser rules** (`parseHint(text, cardType)` in `_ruby.js`):

1. Split `text` on `<br>`.
2. For each trimmed line:
   - If it matches `^(hanzi|audio|production)\s*:\s*(.+)$` (case-insensitive) and the prefix equals `cardType` → strip prefix, keep the body.
   - If it matches the prefix pattern but the prefix is one of the three known card types **and** does **not** equal `cardType` → skip.
   - Otherwise (no recognized prefix) → keep the line as-is.
3. Concatenate kept lines with `<br>` for rendering.

### Examples

| `Hint` value | hanzi-front | audio-front | production-front |
|---|---|---|---|
| `doubled syllable + 的` | ✓ same | ✓ same | ✓ same |
| `hanzi: starts with 杠<br>audio: doubled syllable<br>production: northeastern flavor` | `starts with 杠` | `doubled syllable` | `northeastern flavor` |
| `northeastern slang<br>audio: doubled syllable` | `northeastern slang` | `northeastern slang<br>doubled syllable` | `northeastern slang` |

The mixed case is intentional and useful: a universal base hint plus card-specific augmentation.

### Edge cases

- Empty parse result (e.g. `Hint` only contains lines tagged for a different card type than the current one) → no hint button rendered. Same as empty `Hint` field.
- A line like `note: this is informal` does NOT match a known card type → kept as universal. Validator warns about unrecognized prefixes (likely typo for `production:`).
- **No escape syntax for a literal line starting with a recognized prefix.** A line like `production: this hint is intentionally tagged` will always be treated as production-card-specific — there is no way to write a universal hint whose body literally begins `production:`. Acceptable trade-off: the collision is rare, and if it does come up the user can rephrase the line. If this ever becomes painful, a future iteration can add a leading-backslash escape (`\production:`) without breaking existing data.

## Card template behavior

### Production front (`production_front.html`)

```html
<div class="card-side card-front">
  {{#Context}}<div class="context-prompt">{{Context}}</div>{{/Context}}
  <div class="english-prompt">{{English}}</div>
  {{#Hint}}<div class="hint-mount" data-hint="{{text:Hint}}" data-card-type="production"></div>{{/Hint}}
</div>
<script src="_ruby.js"></script>
<script>(function () { window.ankiDecks.mountHint(".hint-mount"); })();</script>
```

- `Context` always-visible above the English prompt, small + muted.
- `Hint` renders as a "Show hint" button if `parseHint` returns non-empty; clicking expands the parsed text in place.

### Hanzi-recognition front, audio-recognition front

Add the same hint mount with `data-card-type="hanzi"` / `data-card-type="audio"`. Existing front content (ruby block + toggle / audio button) unchanged. No `Context` on these fronts — the Hanzi or audio already disambiguates the answer.

### All 3 backs (`*_back.html`)

- `{{#Context}}` line rendered above `{{#Note}}` when populated. Small label `Context:` + value. Styled like `.note` (muted body text).
- `{{#Hint}}` mount with `data-revealed="true"` and the same `data-card-type` as the matching front (production back gets `production`, hanzi-recognition back gets `hanzi`, audio-recognition back gets `audio`). The same `mountHint` helper detects the `revealed` attribute and renders the parsed hint as a labeled line (`Hint:` + parsed text) instead of a button. Per-card-type filtering on backs is intentional: each back mirrors its own front's hint so the user reinforces exactly the clue they saw (or could have seen) before answering.

### `_ruby.js` additions

```js
function parseHint(text, cardType) {
  if (!text) return "";
  const known = new Set(["hanzi", "audio", "production"]);
  const lines = text.split(/<br\s*\/?>/i);
  const kept = [];
  const re = /^([A-Za-z]+)\s*:\s*(.+)$/;
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    const m = line.match(re);
    if (m && known.has(m[1].toLowerCase())) {
      if (m[1].toLowerCase() === cardType) kept.push(m[2].trim());
      // else skip (matches a different card type)
    } else {
      kept.push(line);
    }
  }
  return kept.join("<br>");
}

function mountHint(selector) {
  document.querySelectorAll(selector).forEach((el) => {
    const cardType = el.dataset.cardType;
    const parsed = parseHint(el.dataset.hint, cardType);
    if (!parsed) { el.remove(); return; }
    const revealed = el.dataset.revealed === "true";
    if (revealed) {
      el.innerHTML = '<span class="hint-label">Hint:</span> <span class="hint-text">' + parsed + '</span>';
      el.classList.add("hint-revealed");
    } else {
      const btn = document.createElement("button");
      btn.className = "hint-btn";
      btn.type = "button";
      btn.textContent = "Show hint";
      btn.addEventListener("click", () => {
        el.innerHTML = '<span class="hint-label">Hint:</span> <span class="hint-text">' + parsed + '</span>';
        el.classList.add("hint-revealed");
      });
      el.appendChild(btn);
    }
  });
}

window.ankiDecks.parseHint = parseHint;
window.ankiDecks.mountHint = mountHint;
```

## Styling (`styles.css`)

New rules to add (alongside existing `.english-prompt` / `.note` / `.hint-btn`):

- `.context-prompt` — font-size 14px, color `#6b7280`, font-style italic, text-align center, margin `0 0 8px 0` (sits above `.english-prompt`).
- Night mode override matching `.note`'s pattern.
- `.hint-revealed` — display block, font-size 14px, color matches `.note`, margin `8px 0`, text-align center on fronts (override on backs to inherit normal flow).
- `.hint-label` — same uppercase + letter-spaced treatment as existing column labels (matches `.member-label` on the radical card).

Reuse existing `.hint-btn` for the reveal button. No new button styles.

## Backward compatibility + migration

- Existing rows have 8 columns. After the schema bump they need two empty trailing tabs each. One-shot script `scripts/append_empty_cols.py` (throwaway, deleted after the migration commit) reads each word-deck TSV, preserves the directive block, appends `\t\t` to every data row, writes back. No reordering, no field changes — zero risk to existing data.
- Re-importing the migrated TSVs into Anki is a no-op for content. The note type gains two new empty fields. Anki's `Hanzi` first-field match still works.
- Existing Anki notes built before the bump retain their data; the two new fields simply render empty (and conditional `{{#…}}` blocks collapse cleanly).

## Validator (`scripts/validate.py`)

- Validator already reads the column header from the `#columns:` directive, so the wider schema is picked up automatically.
- Add two new optional-field rules:
  - `Context` and `Hint` are optional (empty allowed).
  - Warn (not error) when either exceeds 120 chars — encourages terseness.
  - For `Hint`: when a line starts with `WORD:` where `WORD` is alphabetic and not in `{hanzi, audio, production}`, emit a warning ("unrecognized card-type prefix; treated as universal"). Catches typos like `prod:` for `production:`.

## INDEX renderer (`scripts/index.py`)

- `Context` rendered as a small muted line next to the English gloss in each deck row (similar to existing per-row note rendering).
- `Hint` skipped on the INDEX. It's per-card study help, not browse data.

## Note type install (`note_type/Chinese_anki_decks/README.md`)

Field list in the install instructions updates from 9 → 11 fields, in this order:

```
Hanzi
Pinyin
English
Breakdown
Examples
Note
Context
Hint
Link
PersonalNote
Audio
```

`PersonalNote` + `Audio` continue to be Anki-only (never in TSV).

Add a short section documenting the `Hint` prefix format with the table from this design doc.

## `CLAUDE.md` updates

Schema section for word decks bumps to 10 columns. Document:

- `Context` purpose, length guidance, examples (slang register, dialect tag, scenario qualifier).
- `Hint` purpose, prefix format, parser semantics, examples table.
- Both are optional. Migration: existing rows get empty values; new rows populate as needed.

## Files touched

- `Chinese_Core_Conversation.tsv` — directive + `\t\t` per row
- `Chinese_Idioms_Proverbs_Classical.tsv` — same
- `Chinese_Slang_Dialect_Flavor.tsv` — same
- `note_type/Chinese_anki_decks/styles.css` — new classes
- `note_type/Chinese_anki_decks/production_front.html` — Context + Hint mounts
- `note_type/Chinese_anki_decks/production_back.html` — Context line + Hint mount (revealed)
- `note_type/Chinese_anki_decks/hanzi_recognition_front.html` — Hint mount
- `note_type/Chinese_anki_decks/hanzi_recognition_back.html` — Context line + Hint mount (revealed)
- `note_type/Chinese_anki_decks/audio_recognition_front.html` — Hint mount
- `note_type/Chinese_anki_decks/audio_recognition_back.html` — Context line + Hint mount (revealed)
- `note_type/Chinese_anki_decks/_ruby.js` — `parseHint`, `mountHint`
- `note_type/Chinese_anki_decks/README.md` — field list + Hint format docs
- `scripts/validate.py` — Context + Hint validation rules
- `scripts/index.py` — render Context column
- `CLAUDE.md` — schema section update
- `scripts/append_empty_cols.py` *(throwaway one-shot migration script; deleted in the same commit as the migration)*

## Verification

1. **Migration**: run `scripts/append_empty_cols.py` against all three TSVs. Diff shows only trailing `\t\t` added per data row + directive update. Row count unchanged.
2. **Validator**: `python scripts/validate.py` clean against the migrated TSVs (zero errors; warnings only for any deliberately added test rows with long Context/Hint).
3. **INDEX**: `python scripts/index.py`, open `INDEX.html`. Context renders next to English on the few rows seeded with the field; nothing breaks for rows without it.
4. **Anki import**:
   - Re-import each TSV into a scratch Anki profile. Confirm: existing notes keep all data; new fields show empty; no duplicates created (first-field match still works).
   - Add a Context value to one slang row (e.g. `Northeastern slang` on 杠杠的), re-import. The production front of that note shows the Context line above the English. Production back shows Context above Note.
   - Add a multi-line Hint with per-card prefixes to a separate row. Walk through all 3 cards: confirm front-side button reveals only the matching line; back-side auto-shows the matching line; the per-card targeting works.
   - Add a universal-only Hint (no prefix) to another row. Confirm same hint appears on all 3 fronts.
5. **Backward compat**: spot-check 10 rows that have empty Context + Hint. Confirm cards render identically to before the change.
