---
name: anki-import
description: >
  Use when the user pastes one or more Chinese words / phrases to add to the
  anki-decks repo, or invokes /anki-import. Accepts any count from a single
  entry to a large batch — works the same either way. Parses loose input,
  fills missing fields (pinyin, English, note), categorizes per deck, picks
  tier + topical tags from TAGS.md, dedupes against all decks, shows a
  review table, appends accepted rows, then runs the validator and
  regenerates INDEX.html.
---

# anki-import

Pipeline for adding Chinese vocab / phrases to the project's three TSV decks
without the user having to categorize or tag anything by hand.

## When to activate

Activate when **any** of these is true:

- User invokes `/anki-import`.
- User says "add these to my decks", "categorize and add", "import these",
  "save these to anki", or similar.
- User pastes a block of text that contains Hanzi characters and there is no
  other framing for the message (e.g. it isn't being analyzed, translated,
  or quoted as part of a different task).

If ambiguous (e.g. user pastes a single phrase mid-conversation), ask once:
**"Import to decks?"** If they say yes, run the full pipeline.

This skill works for 1 entry or 100 — there is no separate single-entry path.

## Read these first (every invocation)

Always re-read these before producing the review table — pick up changes the
user may have made between sessions:

- `CLAUDE.md` — scope guardrails, schema, deck purposes.
- `TAGS.md` — canonical tag allowlist.
- `Chinese_Core_Conversation.tsv`,
  `Chinese_Idioms_Proverbs_Classical.tsv`,
  `Chinese_Slang_Dialect_Flavor.tsv` — source-of-truth for dedup.

For tag and dedup work, prefer programmatic access via
`scripts/common.py:parse_tsv` and `scripts/common.py:load_allowed_tags`.

## Parse the input

Accept any per-line shape. Strip bullets (`-`, `*`, `•`, numbering like
`1.`), surrounding quotes, and trailing punctuation that's clearly user
shorthand (`,` `;` at end of line).

Supported shapes:

- bare Hanzi only — most common case
- `Hanzi pinyin english`
- `Hanzi — english` or `Hanzi - english`
- `Hanzi (pinyin) english`
- `Hanzi: english`
- lines containing a parenthetical example sentence

One entry per line by default. If a line clearly contains multiple
comma-separated phrases (Chinese `、` or ASCII `,` between Hanzi tokens),
split on those separators. Do **not** split on commas that appear inside an
English gloss.

Lines starting with `#` are comments — skip them.

## Fill missing fields per entry

Schema (column order, same as the TSVs):

```
Hanzi  Pinyin  English  Breakdown  Examples  Note  Link  Tags
```

Rules:

- **Hanzi** — simplified characters only. Never traditional. If input is
  traditional, convert and flag in the review table so the user can confirm.
- **Pinyin** — tone marks always. Never digit tones (`ni3hao3`). Lowercase.
  **Strict one space-separated syllable per CJK character** (e.g. `那个` →
  `nà ge`, `怎么说呢` → `zěn me shuō ne`). The ruby template aligns each
  syllable above each character — the validator hard-errors on mismatched
  counts. Apply `一` / `不` sandhi (`yī` → `yí` before tone 4; `bù` → `bú`
  before tone 4); leave other tones lexical. Skip pinyin for punctuation.
- **English** — concise gloss. Multiple senses separated by ` / `. No
  example sentences here — those go in `Examples`.
- **Breakdown** — per-character gloss, format `char₁ (gloss₁) char₂ (gloss₂) …`.
  Rules:
  - Order chars by first appearance in the Hanzi.
  - Dedup repeated characters (e.g. `君君臣臣` → `君 (ruler) 臣 (minister)`).
  - Skip punctuation (`，` `、` `。` `；` `！` `？` etc.).
  - **Pick the contextual meaning for polysemous characters** — many
    common characters have several meanings. Always pick the one that
    applies *in this specific entry*, not the first dictionary sense.
    Examples: `长` in `吃一堑，长一智` → "gain" (not "long"); `行` in
    `行走` → "walk" (not "row"); `地` in `客观地来讲` → "(adverbial)"
    (not "earth"); `了` in `算了` → "(particle)" (not "finish").
  - Gloss is lowercase English, 1–3 words, no period.
  - **Required for the Idioms deck.** Optional but encouraged elsewhere.
  - Example: `画 (draw) 蛇 (snake) 添 (add) 足 (foot)`.
- **Examples** — 1–3 example sentences. Multiple sentences are separated by
  the literal string `<br>`. Format per sentence: `中文。 / English.` Empty
  if no example. **Use the [`example-sentences`](../example-sentences/SKILL.md)
  skill to generate or source these** — it enforces the quality bar
  (modern, conversational, 5–15 chars, no literary fluff) and outputs
  the exact TSV form.
- **Note** — register warnings, etymology, cultural context, nuance.
  Anything else worth saying that doesn't fit the dedicated fields. Empty
  unless useful.
- **Link** — URL to external info. Two-tier policy:
  - **Primary**: [chineseidioms.com](https://www.chineseidioms.com) when it
    documents the entry:
    - Chengyu / proverbs: `https://www.chineseidioms.com/blog/<pinyin>` where
      `<pinyin>` is the Pinyin field with tones stripped, lowercased, and
      spaces replaced by `-`. Fill this for **every Idioms-deck row** (the
      site has 1085+ chengyu and the algorithmic URL is reliable; verified
      end-to-end via `scripts/find_site_links.py`).
    - Internet slang: `https://www.chineseidioms.com/slang/<slug>` — slugs
      are inconsistent (e.g. 割韭菜 → `gao-ji`, 老六 → `lao-liu-bi`). Look up
      against [the slang index](https://www.chineseidioms.com/slang) by hand;
      do not derive from pinyin.
    - Everyday phrases: `https://www.chineseidioms.com/phrases/<slug>` —
      mostly hyphenated pinyin but with quirks (e.g. 算了 → `suan-le-phrase`).
      Look up against [the phrases index](https://www.chineseidioms.com/phrases).
  - **Fallback**: MDBG dictionary lookup, for any row not on
    chineseidioms.com: `https://www.mdbg.net/chinese/dictionary?wdqb=<url-encoded-hanzi>`.
    Universal coverage. Use this for Core / Slang rows that have no richer
    home — every new entry should have *some* Link.
  - Never invent a chineseidioms.com URL you haven't verified; MDBG is the
    safe default when in doubt.
- **Tags** — see "Pick tags" below.

The TSVs do not have Audio or PersonalNote columns. The note type has
`Audio` (HyperTTS-filled) and `PersonalNote` (user-only) fields that live
only inside Anki; the import never touches them.

## Pick deck per entry

Per `CLAUDE.md`:

| Deck | Picks |
|------|-------|
| Core (`Chinese_Core_Conversation.tsv`) | Practical, default-way-to-say-it daily vocab and phrases. Conversation glue, reactions, fillers, opinions, daily-life nouns. |
| Idioms (`Chinese_Idioms_Proverbs_Classical.tsv`) | Chengyu, proverbs, classical / literary phrases, poetic flavor. |
| Slang (`Chinese_Slang_Dialect_Flavor.tsv`) | Modern slang, internet slang, regional dialect, old slang, mildly vulgar. Non-standard or fun-extra-flavor. |

Disambiguation rule (verbatim from `CLAUDE.md`):

> If it's the default way Mandarin speakers say something, it's Core. If
> it's an extra flavorful alternative, it's Slang.

Four-character idioms → Idioms even if widely used. Erhua-flavored or
regional → Slang. Internet-origin terms → Slang.

## Pick tier tag

Exactly one per entry:

| Tag | Use when |
|-----|----------|
| `production-ready` | High-frequency spoken, register-safe for active daily use. |
| `recognition-ready` | Should recognize; occasional active use OK. |
| `recognition-first` | Register-sensitive, regional, literary, dated, or low active-use priority. Default for Idioms / Slang entries unless clearly daily-spoken. |

## Pick topical tags

Strict allowlist — only tags listed in `TAGS.md`. Use
`scripts/common.py:load_allowed_tags()` to read it.

If an entry genuinely needs a tag that doesn't exist in `TAGS.md`:

- **Do not** sneak the tag into the row.
- **Do** surface it in the review table under a "new tags proposed"
  section so the user explicitly accepts the addition. If accepted, add it
  to `TAGS.md` in the right section before appending the row.

Keep tag count reasonable (typically 1 tier tag + 1-3 topical tags). Reuse
existing tags over inventing near-synonyms.

## Dedupe

Before showing the review table, run dedup over all three TSVs:

```python
import sys
sys.path.insert(0, "scripts")
from common import parse_tsv, deck_paths

existing = {}
for p in deck_paths():
    _, rows = parse_tsv(p)
    for r in rows:
        existing.setdefault(r.hanzi, (p.name, r.line_no))
```

Any candidate whose Hanzi is already a key goes to the **"skipped
(duplicate)"** section of the review table, annotated with
`existing at <file>:<line>`. It is **never** appended.

## Review table

Single Markdown table with these columns, in this order:

```
# | deck | hanzi | pinyin | english | tier | tags | breakdown | examples | note | link
```

The `breakdown`, `examples`, `note`, and `link` cells can be empty. Truncate
long values in the table display (e.g. show first 40 chars of an example
with `…`) so the table stays readable.

Below it:

- **"Skipped (duplicate)"** — short list of candidates that already exist,
  with their existing location.
- **"New tags proposed"** — any tags from this batch not yet in `TAGS.md`,
  with proposed section and one-line definition. Empty if none.

The user replies with one of:

- `all` — accept every row in the main table.
- a number list / range like `1-5, 8, 11` — accept those rows only.
- `drop 3, 7` — remove those rows from the accept set (use after `all`).
- `row 4: change deck to slang, tier recognition-first` — edit a row before
  acceptance. Re-render the table after edits.
- `cancel` — abort, append nothing.

## Append accepted rows

Programmatic append only — never run `scripts/add.py` from this skill
(it's interactive). Use `scripts/common.py:append_row`:

```python
import sys
sys.path.insert(0, "scripts")
from common import append_row, REPO_ROOT, DECKS

deck_key = "core"   # or "idioms" / "slang"
path = REPO_ROOT / DECKS[deck_key]
append_row(path, [hanzi, pinyin, english, breakdown, examples, note, link, tags_str])
```

`tags_str` is space-separated, tier tag first by convention. Any field can
be the empty string; only `Hanzi` / `Pinyin` / `English` are required.

Append one TSV at a time. If new tags were approved, edit `TAGS.md` first
(add entry under the right section), then append rows.

## Always run after appending

In this order, from the repo root:

```
python scripts/validate.py
python scripts/index.py
```

Required: validator exits 0. If errors are reported, **do not** continue
to the report step — surface the validator output to the user and ask how
to proceed. Warnings (e.g. missing tier tag) are non-fatal.

`scripts/index.py` regenerates `INDEX.html`. No errors expected.

## Report back

After successful append + validate + index, summarize:

- N appended per deck (e.g. "Core: 4 · Slang: 2 · Idioms: 0").
- M duplicates skipped.
- New tags added to `TAGS.md` (if any).
- Validator summary line (e.g. "checked 3 file(s): 0 error(s), 71
  warning(s)").
- "INDEX.html regenerated."

Keep it short — the user already saw the accepted table.

## Red flags / refuse

Never:

- Silently invent a tag not in `TAGS.md`.
- Edit an existing row (decks are append-only).
- Reorder existing rows.
- Write traditional characters into the Hanzi column.
- Put example sentences in the English column.
- Run `scripts/add.py` non-interactively.
- Continue past a validator error.

If the user's input includes content that clearly belongs in a grammar
course (verb-conjugation drills, character-radical study, measure-word
tables, sentence-pattern fill-ins), call it out under a separate
"out of scope (skipped)" section of the review table rather than forcing
it into a deck. See `CLAUDE.md` "Scope guardrails".
