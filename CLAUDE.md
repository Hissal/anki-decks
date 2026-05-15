# Anki Decks — Chinese Vocabulary

## What this is

Personal Anki decks for Chinese language learning. **Not a course** — assumes other resources cover grammar and structured study. These decks **augment** that with vocabulary, common spoken phrases, and flavor.

Four decks, four scopes:

| File | Scope |
|------|-------|
| `Chinese_Core_Conversation.tsv` | Everyday useful vocab and phrases. Conversation glue, reactions, fillers, opinions, daily-life nouns. The "actually useful" deck. |
| `Chinese_Idioms_Proverbs_Classical.tsv` | Chengyu, proverbs, classical/literary phrases, poetic flavor. "Ancient wisdom" feel. |
| `Chinese_Slang_Dialect_Flavor.tsv` | Modern slang, internet slang, regional dialect, old-school slang, mildly vulgar — anything non-standard or just fun extra flavor. |
| `Chinese_Phonetic_Components.tsv` | Phonetic components — the sound-bearing radicals that recur across many compound characters. Different schema from the other three; see the **Phonetic Components deck** section below. |

If something fits multiple decks, pick the one that matches the *primary vibe* — don't duplicate. The phonetic-components deck is an exception: a Hanzi character can legitimately appear there as a *component* even if it also exists as a word in one of the other decks. The components deck lives in its own ontology (components ≠ words).

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

## Phonetic Components deck

`Chinese_Phonetic_Components.tsv` is the fourth deck and has its own schema, note type, and tooling. Purpose: drill recognition of the recurring **phonetic components** that signal the sound of a compound character. ~80% of Hanzi are phono-semantic compounds, so knowing the phonetic side cuts pronunciation guessing dramatically. The deck is *recognition*-focused — it does not teach the components as standalone words.

### Schema

16 columns. Directive block:

```
#separator:tab
#html:true
#columns:Key	Component	Pinyin	Meaning	MemberChars	SameSyllableChars	Reliability	Productivity	Frequency	Decomposition	MemberDecomp	CrossRefs	Note	Link	Audio	Tags
#tags column:16
```

1. `Key` — `<component>:<numeric-pinyin>` (e.g. `肖:qiao4`). Anki's first field must be unique per note, and the same component can produce multiple sounds (`肖` → xiāo / qiào / shāo), so `Component` alone is not unique. Card templates never display `Key` — it exists only to dedupe and to drive Anki's match-on-first-field import behavior.
2. `Component` — the lone phonetic component (e.g. `工`). Single CJK character per row.
3. `Pinyin` — the sound the component produces in derivative characters, with tone marks (e.g. `gǒng` for `工` as it appears in `巩鞏汞銾`). Note: this is the sound of the **compound**, not necessarily the component's own dictionary pronunciation. Card templates tone-color this field automatically based on the diacritic.
4. `Meaning` — English gloss from HanziCraft's dictionary (CC-CEDICT-derived), with senses ` / `-separated. Phase 2 enrichment overwrites the rough phase-1 mnemonics; if HanziCraft has no entry we fall back to whatever the source notes file had.
5. `MemberChars` — bucket 1. The set of compound characters that take this row's exact sound (matching pinyin including tone). Comes from the source's curated set; the component itself is stripped so the front of Card 2 is a real recognition test.
6. `SameSyllableChars` — bucket 2. Characters that contain this component AND share its syllable but DIFFER in tone (e.g. for `工:gōng`, this is `巩鞏汞銾` — same `gong` syllable but tone 3). Derived from HanziCraft's full member-char list (`scripts/cache/component_cwc.json`) plus per-char pinyin (`scripts/cache/char_data.json`); chars already in MemberChars are excluded. Empty when no bucket-2 chars exist.
7. `Reliability` — productivity stats: `X/Y` (sound match across all chars containing the component) and/or `X/Y (ignoring tone)`. Multiple stats joined with ` · `.
8. `Productivity` — HanziCraft's "appears as a component in N characters" count (e.g. `121` for `工`). Total number of characters that contain this component, regardless of whether they take its sound. Used to compute bucket-3 ("also a component in N more chars, different syllable") as `Productivity − len(MemberChars) − len(SameSyllableChars)`.
9. `Frequency` — HanziCraft's frequency rank for the component as a standalone character (e.g. `118` for `工` being the 118th most frequent character in modern usage). Empty for rare components not in the frequency list.
10. `Decomposition` — TSV-packed top-level + radical breakdown of the component itself: `once:<a>+<b>` (top-level split, e.g. `once:一+丄` for `工`) and optionally `;radical:<r>` (canonical Kangxi radical, only when it differs from the component). `?` stands in for HanziCraft's "no glyph available" placeholder. Card templates parse this and render it as labeled lines on Card 1 back.
11. `MemberDecomp` — per-bucket-char once-level decomposition packed as `巩=工+凡|汞=工+水|銾=金+巠`. One entry per char in MemberChars + SameSyllableChars (skipped when HanziCraft has no usable decomp for that char). Card 2 back uses this to draw `巩 = 工 + 凡` lines under each bucket with the phonetic component highlighted.
12. `CrossRefs` — for the 33 components in the deck with multiple readings, the OTHER readings of the same component packed as `qiào / 俏峭鞘诮 · shāo / 稍梢捎艄筲`. Empty for single-reading components. Card 1 back renders this as a tone-colored "also reads" block.
13. `Note` — free-form. Used for variant/traditional forms (`Traditional: 歷`), expanded exception hints (`Exceptions (different sound): 毕昆皆毚`), related-char hints (`Also related: 位`), similarity warnings, and other context. Phase 3 dropped HanziCraft mnemonic-style entries; meanings + decomposition + the HanziCraft link replace them.
14. `Link` — HanziCraft URL covering the component plus all its member chars, e.g. `https://hanzicraft.com/dashboard/character/%E5%B7%A5%E5%B7%A9%E9%9E%8F%E6%B1%9E%E9%8A%BE`. Clicking opens HanziCraft's dashboard for the whole set at once. Rendered as a "HanziCraft →" footer on each card back.
15. `Audio` — `[sound:…\.mp3]` ref. Files are user-supplied; cards display fine without them, audio just no-ops until mp3s are dropped into `collection.media`.
16. `Tags` — every row has at least `phonetic-component`.

The deck generates **two cards per note**: Card 1 (Component → Sound) shows the lone component, asks for the sound. Card 2 (Set → Sound) shows the member-char set, asks for the shared phonetic and its sound. Note type lives at `note_type/PhoneticComponent/`.

### Tooling

- **`scripts/import_phonetic_components.py`** — one-shot generator. Reads the rough HanziCraft-derived source notes file, optionally merges in HanziCraft enrichment, and writes the deck TSV. Not idempotent; overwrites on every run. Phase-1 cleanup includes pinyin tonemark conversion, reliability parsing, multi-line row repair, HTML-entity stripping, column-misalignment fixes, and merge-on-dedup. Phase-2 enrichment layers in Meaning (overrides mnemonics), Productivity, Frequency, and Link from the cached HanziCraft data.
- **`scripts/cache/hanzicraft.json`** — cached HanziCraft API responses keyed by component character. Generated by hitting `/api/internal/character/<char>` for each unique component via an authenticated browser session and saving the relevant fields (definition, frequency rank, productivity count, decomposition). Committed so phase 2 is reproducible without re-fetching. Re-run the fetch when you add new components to the source.
- **`scripts/cache/component_cwc.json`** — per-component "chars-with-this-component" list, e.g. `{"工": ["巩", "汞", "鞏", ...]}`. Populates the source for bucket-2 and bucket-3 reasoning on Card 2 back. Generated by the same authenticated-session pass.
- **`scripts/cache/char_data.json`** — per-character pinyin keyed by Hanzi, e.g. `{"巩": {"pinyin": "gong3"}, ...}`. Covers every char that appears across all `component_cwc.json` lists (~5900 chars). Used at import time to classify each cwc char into bucket 2 (same syllable, different tone) vs bucket 3 (different syllable, count only).
- **`scripts/cache/char_decomp.json`** — per-character once-level decomposition keyed by Hanzi, e.g. `{"巩": {"once": ["工", "凡"]}, ...}`. Covers the ~2440 unique chars across all rows' MemberChars + SameSyllableChars. Used at import time to build the `MemberDecomp` column rendered on Card 2 back.
- **`scripts/validate_components.py`** — sibling of `validate.py` for the new schema. Hard errors on missing required fields, non-CJK components, digit-tone pinyin, MemberChars still containing the component, non-integer Productivity/Frequency, and duplicate Keys.
- **`scripts/index.py`** — extended to render a Phonetic Components section alongside the word decks in `INDEX.html`.
- **`scripts/common.py`** — `deck_paths()` is scoped to word decks only (`WORD_DECK_FILES`), so the existing word-deck tooling never sees the components TSV. The components deck has its own parser in `scripts/components_common.py`.

### Cross-deck duplication

The "don't duplicate the same Hanzi across decks" rule applies only to the word decks. The components deck is exempt: a Hanzi like `工` can legitimately appear in `Core` (as the word "work") and in `Components` (as the phonetic component). They are different mental objects.

## Things to NOT do

- Don't reorder rows.
- Don't add per-row novelty tags ("misc-2024-05-11") — tags should be reusable.
- Don't duplicate the same Hanzi across decks.
- Don't put example sentences in the `English` column — those go in `Examples`.
- Don't cram per-char gloss into `Note` — it has its own `Breakdown` column.
- Don't break the per-character pinyin alignment (one space-separated syllable per CJK char).
- Don't write traditional characters. Simplified only.
