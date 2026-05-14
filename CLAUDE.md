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

All three files share the same schema. **TSV, tab-separated, UTF-8.** Each file starts with Anki import directives (lines prefixed with `#`) — the `#columns:` directive doubles as the header, so there is no separate header row.

Required directive block at the top of every deck file:

```
#separator:tab
#html:true
#columns:Hanzi	Pinyin	English	Breakdown	Examples	Note	Link	Tags
#tags column:8
```

Columns (in order):

1. `Hanzi` — simplified characters only.
2. `Pinyin` — with tone marks (lowercase). **Strict one syllable per CJK character, space-separated.** E.g. `那个` → `nà ge`, `怎么说呢` → `zěn me shuō ne`. The ruby template aligns each syllable above each character, so the count must match. The validator enforces this. Tone sandhi for `一` and `不` is applied at the morpheme level (`yī` → `yí` before tone 4; `bù` → `bú` before tone 4); other sandhi (third-tone, neutral-tone variants) stays lexical.
3. `English` — short gloss. Multiple senses separated by `/`.
4. `Breakdown` — per-character gloss, format `char₁ (gloss₁) char₂ (gloss₂) …`. Order by first appearance in Hanzi. Dedup repeated characters. Skip punctuation. Gloss text lowercase English, 1–3 words, no period. **For polysemous characters pick the meaning that applies in this entry's context, not the first dictionary sense** (e.g. `长` in `吃一堑，长一智` → "gain"; `地` in `客观地来讲` → "(adverbial)"; `了` in `算了` → "(particle)"). Convention is to fill this for the idioms deck; optional but encouraged elsewhere. Example: `画 (draw) 蛇 (snake) 添 (add) 足 (foot)`.
5. `Examples` — 1–3 example sentences. Multiple sentences are separated by literal `<br>` (Anki renders that as a line break with `#html:true` set). Format per chunk: `中文句子。 / English translation.` Pinyin does **not** appear here — the ruby template generates pinyin from the Hanzi field. The card template splits Examples on `<br>` for the bulleted list and on ` / ` for the Chinese/English pair. Generate via the [`example-sentences`](.claude/skills/example-sentences/SKILL.md) skill — it enforces the quality bar (modern, conversational, 5–15 chars). Empty if no example.
6. `Note` — anything else worth saying: register warnings, etymology, cultural context, nuance.
7. `Link` — URL pointing at external info. Two sources, in this priority order:
   - **[chineseidioms.com](https://www.chineseidioms.com)** when it has the entry. URL patterns:
     - Chengyu / proverbs: `https://www.chineseidioms.com/blog/<pinyin-hyphenated-notones>` — algorithmic from the per-character Pinyin (drop tones, lowercase, hyphenate). The idioms deck uses this for every row.
     - Internet slang: `https://www.chineseidioms.com/slang/<slug>` — slugs are inconsistent; check the [/slang index](https://www.chineseidioms.com/slang) before guessing.
     - Everyday phrases: `https://www.chineseidioms.com/phrases/<slug>` — mostly hyphenated pinyin but with quirks; check the [/phrases index](https://www.chineseidioms.com/phrases).
   - **MDBG dictionary fallback** for anything not on chineseidioms.com: `https://www.mdbg.net/chinese/dictionary?wdqb=<url-encoded-hanzi>`. Universal coverage, just dictionary glosses — used as the fallback for Core / Slang rows the project couldn't match to a richer source.
   - Use `scripts/find_site_links.py` to bulk-apply: `--apply` writes chineseidioms.com matches only; `--apply --mdbg-fallback` also fills the rest with MDBG URLs. The script never overwrites an existing Link value.
8. `Tags` — space-separated tags. See tag conventions below.

The Anki note type has two additional fields that **never appear in TSV**: `Audio` (for `[sound:file.mp3]` references) and `PersonalNote` (free-form user notes added inside Anki). Because they are omitted from the `#columns:` directive, Anki preserves them untouched on every re-import.

**Hanzi (column 1) is the deck's de-facto unique key.** Anki import is set to match on first field, so re-importing a row with the same Hanzi *updates* the existing note rather than creating a duplicate.

## Workflow

The TSV files are **append-only**. Adding new vocab:

1. Append rows to the appropriate TSV (no edits to existing rows unless fixing a mistake).
2. Re-import into Anki — Anki matches by first field (Hanzi) and updates existing notes / adds new ones. The directive block tells Anki the separator, column-to-field mapping, and which column holds tags.
3. Commit.

Do not reorder existing rows. Do not strip or reorder the directive block at the top of each file.

## Tag conventions

Two kinds of tags coexist in column 8:

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
- Don't add per-row novelty tags ("misc-2024-05-11") — tags should be reusable.
- Don't duplicate the same Hanzi across decks.
- Don't put example sentences in the `English` column — those go in `Examples`.
- Don't cram per-char gloss into `Note` — it has its own `Breakdown` column.
- Don't break the per-character pinyin alignment (one space-separated syllable per CJK char).
- Don't write traditional characters. Simplified only.
