---
name: anki-suggest
description: >
  Use when the user wants suggested new Chinese entries to skim before
  adding to the anki-decks repo. Triggers on /anki-suggest, "suggest some
  X for my deck", "give me N new ones", or any request for candidate
  vocabulary. Generates a deduped table of candidates respecting project
  scope, then hands accepted rows off to the anki-import skill for the
  actual append.
---

# anki-suggest

Candidate generator for the project's three TSV decks. Output goes to a
review table — the user picks what to keep, accepted rows are routed
through `anki-import` so dedup + validation + index regeneration happen
exactly once and in one place.

## When to activate

Activate when:

- User invokes `/anki-suggest`.
- User says "suggest some X for my decks", "give me N new ones", "what
  could I add for <theme>", or asks for a candidate list to skim.

Do **not** auto-trigger when the user pastes their own entries — that's
`anki-import`.

## Clarify the request (one round, only if needed)

If the user already specified deck, theme, and count, skip this. Otherwise
ask in one round:

| Slot | Default if unspecified |
|------|------------------------|
| Target deck | `any` (pick per entry) |
| Theme / category | `open` (model picks for variety) |
| Count | `12` |
| Tier preference | mixed; `production-ready` biased for Core; `recognition-first` biased for Idioms / Slang |

## Read these first (every invocation)

- `CLAUDE.md` — scope guardrails and deck purposes.
- `TAGS.md` — canonical tag allowlist; suggestions must use existing tags.
- All three TSVs — for dedup before showing the table.

Programmatic access via `scripts/common.py:parse_tsv` and
`scripts/common.py:load_allowed_tags`.

## Scope guard (this project is augmentation, not a course)

From `CLAUDE.md`:

> Not a course — assumes other resources cover grammar and structured
> study. These decks augment that with vocabulary, common spoken phrases,
> and flavor.

Skip anything that belongs in a grammar course: verb-conjugation drills,
character / radical study, measure-word tables, fixed sentence-pattern
fill-ins as standalone entries. Bias every suggestion toward what is
genuinely heard or used.

Per deck:

| Deck | Bias |
|------|------|
| Core | High-frequency spoken vocab and phrases. Conversation glue, reactions, fillers, opinions, daily-life nouns. The "default-way-to-say-it" choice. |
| Idioms | Chengyu, proverbs, classical / literary phrases, poetic flavor. Recognition-first by default. |
| Slang | Modern slang, internet, regional dialect, mildly vulgar, fun extra flavor. Non-standard or playful. |

## Generate candidates

Produce N entries, each pre-structured as a future import row:

```
deck | hanzi | pinyin | english | tier | tags | breakdown | examples | note | link
```

Rules:

- **Diversity** within the batch — don't return 12 near-synonyms. Vary
  topic, register, length, and grammatical role.
- **Tags** strictly from `TAGS.md`. If a strong candidate would need a
  brand-new tag, drop the candidate in favor of one that fits the
  existing taxonomy.
- **Tier** picked per the same rules `anki-import` uses (see that skill's
  "Pick tier tag" section).
- **Pinyin** always with tone marks, never digit tones. **Strict one
  space-separated syllable per CJK character** (e.g. `那个` → `nà ge`).
  Apply `一` / `不` sandhi; leave other tones lexical.
- **Hanzi** simplified only.
- **Breakdown (required for Idioms candidates, encouraged elsewhere)** —
  per-character gloss: `char₁ (gloss₁) char₂ (gloss₂) …`. Order by first
  appearance, dedup repeated chars, skip punctuation, **pick the
  contextual meaning for polysemous characters** (many common chars have
  multiple senses — pick the one that applies here, not the first
  dictionary sense), lowercase 1–3 words per gloss. See `anki-import`
  SKILL.md "Breakdown" section for the authoritative spec.
- **Examples** — 1–3 example sentences separated by `<br>`. Format per
  sentence: `中文。 / English.` **Use the
  [`example-sentences`](../example-sentences/SKILL.md) skill to generate
  them** — it enforces the quality bar (modern, conversational, 5–15
  chars, no literary fluff).
- **Note** — register warnings, etymology, cultural context. Optional.
- **Link** — see `anki-import` SKILL.md "Link" section. For Idioms, fill
  algorithmically from Pinyin (`https://www.chineseidioms.com/blog/<pinyin-hyphenated-notones>`).
  For Slang / Core, look up against [chineseidioms.com/slang](https://www.chineseidioms.com/slang)
  or [chineseidioms.com/phrases](https://www.chineseidioms.com/phrases) —
  do not derive from pinyin (slugs are inconsistent). For anything not on
  chineseidioms.com, fall back to MDBG:
  `https://www.mdbg.net/chinese/dictionary?wdqb=<url-encoded-hanzi>`.

## Dedupe before showing

Drop candidates whose Hanzi already appears in any deck. If the drop
shrinks the batch below the requested count, top up by generating
replacements until the requested count is met (or signal exhaustion if
the theme is too narrow).

```python
import sys
sys.path.insert(0, "scripts")
from common import parse_tsv, deck_paths

existing = set()
for p in deck_paths():
    _, rows = parse_tsv(p)
    existing.update(r.hanzi for r in rows)
```

Suggestion duplicates against existing rows is treated as a bug — the
user should not see them in the review table.

## Show review table

Use the **same column layout** as `anki-import`'s review table:

```
# | deck | hanzi | pinyin | english | tier | tags | breakdown | examples | note | link
```

Truncate long values (breakdown / examples / note) to keep the table
readable. This keeps the user's mental model consistent across the two
skills.

## Accept user selection

Same vocabulary as `anki-import` — refer to that skill rather than
restating in different words:

- `all`
- number lists / ranges (`1-5, 8, 11`)
- `drop N, M`
- per-row edits (`row 4: change deck to slang, tier recognition-first`)
- `cancel`

## Hand off to `anki-import`

The accepted subset is the input to `anki-import`. Do **not** append
directly from this skill — route everything through `anki-import` so:

- Dedup runs again right before write (in case the user mutated the repo).
- Validator runs after.
- `INDEX.html` is regenerated.
- The user gets exactly one "appended" summary, in the format they
  already know.

If suggestions came with proposed new tags, those go through the same
"new tags proposed" review path that `anki-import` provides.

## Red flags / refuse

Never propose:

- Traditional characters.
- Entries that belong in a grammar course (see "Scope guard" above).
- Duplicates of existing rows — if any slip through dedup, that's a bug,
  not a feature.
- A tag that isn't in `TAGS.md` (without flagging it explicitly as a
  proposed new tag and a one-line definition).
