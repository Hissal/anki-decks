# Anki Decks — Chinese Vocabulary

## What this is

Personal Anki decks for Chinese language learning. **Not a course** — assumes other resources cover grammar and structured study. These decks **augment** that with vocabulary, common spoken phrases, and flavor.

Three decks, three scopes:

| File | Scope |
|------|-------|
| `Chinese_Core_Conversation.tsv` | Everyday useful vocab and phrases. Conversation glue, reactions, fillers, opinions, daily-life nouns. The "actually useful" deck. |
| `Chinese_Idioms_Proverbs_Classical.tsv` | Chengyu, proverbs, classical/literary phrases, poetic flavor. "Ancient wisdom" feel. |
| `Chinese_Slang_Dialect_Flavor.tsv` | Modern slang, internet slang, regional dialect, old-school slang, mildly vulgar — anything non-standard or just fun extra flavor. |

If something fits multiple decks, pick the one that matches the *primary vibe* — don't duplicate.

## File format

All three files share the same schema. **TSV, tab-separated, UTF-8, one header row.**

Columns (in order):

1. `Hanzi` — simplified characters only
2. `Pinyin` — with tone marks (e.g. `nèige`, not `nei4ge`). Lowercase. Spaces between syllables for multi-syllable phrases when natural.
3. `English` — short gloss. Multiple senses separated by `/`.
4. `Note` — usage notes, register warnings, example sentence. Example sentences use the convention: `Example: 中文句子。 / English translation.`
5. `Audio` — currently empty everywhere. Reserved for `[sound:file.mp3]` Anki syntax later.
6. `Tags` — space-separated tags. See tag conventions below.

**Hanzi (column 1) is the deck's de-facto unique key.** Anki import is set to match on first field, so re-importing a row with the same Hanzi *updates* the existing note rather than creating a duplicate.

## Workflow

The TSV files are **append-only**. Adding new vocab:

1. Append rows to the appropriate TSV (no edits to existing rows unless fixing a mistake).
2. Re-import into Anki — Anki matches by first field (Hanzi) and updates existing notes / adds new ones.
3. Commit.

Do not reorder existing rows. Do not strip the header.

## Tag conventions

Two kinds of tags coexist in column 6:

### Tier tags (learning priority)

One per row when relevant:

- `production-ready` — high-frequency, safe to use actively in speech.
- `recognition-ready` — should recognize when heard/read; OK to produce occasionally.
- `recognition-first` — recognize-only for now. Register-sensitive, regional, literary, dated, or just lower-priority for active use.

Newer Core rows have drifted away from using these. When adding new rows, prefer to include a tier tag — it lets Anki filter cards by active vs. passive study.

### Topical / register tags

Free-form, space-separated. Established ones seen in the decks include:

- Register / tone: `slang`, `old-slang`, `internet-slang`, `dialect`, `classical-flavor`, `literary`, `flavor`, `rude-playful`, `tone-risky`, `erhua`
- Function: `conversation-glue`, `filler`, `connector`, `reaction`, `clarification`, `agreement`, `opinion`, `pattern`
- Domain: `food`, `health`, `culture`, `culture-history`, `holiday`, `education`, `technology`, `internet-media`, `media`, `nature`, `language-learning`, `personality`, `relationships`, `skill`, `life-advice`, `emotions`
- Generic: `everyday-vocab`, `useful-phrases`, `chengyu`

Prefer reusing an existing tag over inventing a new near-synonym. Keep tags lowercase, hyphen-separated.

## Scope guardrails

When adding entries, ask:

- **Does this belong here, or in a grammar course?** Skip grammar drills, conjugation tables, raw character/radical study. This is vocab and phrases.
- **Will this actually be heard or used?** Bias toward spoken-frequency over textbook frequency.
- **Which deck?** Core = practical daily. Idioms = chengyu / classical / poetic. Slang = non-standard, regional, vulgar, fun.

If unsure between Core and Slang for a casual word: if it's the **default** way Mandarin speakers say something, it's Core. If it's an extra flavorful alternative, it's Slang.

## Things to NOT do

- Don't reorder rows.
- Don't edit the Audio column unless adding real `[sound:...]` references.
- Don't add per-row novelty tags ("misc-2024-05-11") — tags should be reusable.
- Don't duplicate the same Hanzi across decks.
- Don't put example sentences in the `English` column — those go in `Note`.
- Don't write traditional characters. Simplified only.
