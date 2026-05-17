# Anki Decks — Chinese Vocabulary

## What this is

Personal Anki decks for Chinese language learning. **Not a course** — assumes other resources cover grammar and structured study. These decks **augment** that with vocabulary, common spoken phrases, and flavor.

Five decks, five scopes:

| File | Scope |
|------|-------|
| `Chinese_Core_Conversation.tsv` | Everyday useful vocab and phrases. Conversation glue, reactions, fillers, opinions, daily-life nouns. The "actually useful" deck. |
| `Chinese_Idioms_Proverbs_Classical.tsv` | Chengyu, proverbs, classical/literary phrases, poetic flavor. "Ancient wisdom" feel. |
| `Chinese_Slang_Dialect_Flavor.tsv` | Modern slang, internet slang, regional dialect, old-school slang, mildly vulgar — anything non-standard or just fun extra flavor. |
| `Chinese_Phonetic_Components.tsv` | Phonetic components — the sound-bearing pieces that recur across many compound characters. Different schema from the word decks; see the **Phonetic Components deck** section below. |
| `Chinese_Kangxi_Radicals.tsv` | Kangxi semantic radicals — the meaning-bearing pieces (氵 → water, 心 → emotion, 钅 → metal). Complements the phonetic-components deck. Own schema; see the **Kangxi Radicals deck** section below. |

If something fits multiple decks, pick the one that matches the *primary vibe* — don't duplicate. The components / radicals decks are exceptions: a Hanzi character can legitimately appear in those decks as a *component* (semantic OR phonetic) even when it also exists as a word in one of the others. Components, radicals, and words are different mental objects.

## File format

All three files share the same schema. **TSV, tab-separated, UTF-8.** Each file starts with Anki import directives (lines prefixed with `#`) — the `#columns:` directive doubles as the header, so there is no separate header row.

Required directive block at the top of every deck file:

```
#separator:tab
#html:true
#columns:Hanzi	Pinyin	English	Breakdown	Examples	Note	Context	Hint	Link	Tags
#tags column:10
```

Columns (in order):

1. `Hanzi` — simplified characters only.
2. `Pinyin` — with tone marks (lowercase). **Strict one syllable per CJK character, space-separated.** E.g. `那个` → `nà ge`, `怎么说呢` → `zěn me shuō ne`. The ruby template aligns each syllable above each character, so the count must match. The validator enforces this. Tone sandhi for `一` and `不` is applied at the morpheme level (`yī` → `yí` before tone 4; `bù` → `bú` before tone 4); other sandhi (third-tone, neutral-tone variants) stays lexical.
3. `English` — short gloss. Multiple senses separated by `/`.
4. `Breakdown` — per-character gloss, format `char₁ (gloss₁) char₂ (gloss₂) …`. Order by first appearance in Hanzi. Dedup repeated characters. Skip punctuation. Gloss text lowercase English, 1–3 words, no period. **For polysemous characters pick the meaning that applies in this entry's context, not the first dictionary sense** (e.g. `长` in `吃一堑，长一智` → "gain"; `地` in `客观地来讲` → "(adverbial)"; `了` in `算了` → "(particle)"). Convention is to fill this for the idioms deck; optional but encouraged elsewhere. Example: `画 (draw) 蛇 (snake) 添 (add) 足 (foot)`.
5. `Examples` — 1–3 example sentences. Multiple sentences are separated by literal `<br>` (Anki renders that as a line break with `#html:true` set). Format per chunk: `中文句子。 / English translation.` Pinyin does **not** appear here — the ruby template generates pinyin from the Hanzi field. The card template splits Examples on `<br>` for the bulleted list and on ` / ` for the Chinese/English pair. Generate via the [`example-sentences`](.claude/skills/example-sentences/SKILL.md) skill — it enforces the quality bar (modern, conversational, 5–15 chars). Empty if no example.
6. `Note` — anything else worth saying: register warnings, etymology, cultural context, nuance.
7. `Context` — terse disambiguator (register / region / scenario tag).
   Always-visible on the production front above the English prompt and
   on all 3 backs above the Note line. Use when the English gloss alone
   is ambiguous (e.g. `northeastern slang` for 杠杠的, where the English
   `awesome` matches many possible Mandarin terms). Optional. Keep
   short — 3–8 words.
8. `Hint` — optional click-to-reveal clue rendered on all 3 fronts and
   auto-revealed on all 3 backs. Format: `<br>`-separated lines where
   each line is universal (no prefix → shows on every card) or
   card-scoped via a `hanzi:` / `audio:` / `production:` prefix. See the
   note-type README for the full format table.
9. `Link` — URL pointing at external info. Two sources, in this priority order:
   - **[chineseidioms.com](https://www.chineseidioms.com)** when it has the entry. URL patterns:
     - Chengyu / proverbs: `https://www.chineseidioms.com/blog/<pinyin-hyphenated-notones>` — algorithmic from the per-character Pinyin (drop tones, lowercase, hyphenate). The idioms deck uses this for every row.
     - Internet slang: `https://www.chineseidioms.com/slang/<slug>` — slugs are inconsistent; check the [/slang index](https://www.chineseidioms.com/slang) before guessing.
     - Everyday phrases: `https://www.chineseidioms.com/phrases/<slug>` — mostly hyphenated pinyin but with quirks; check the [/phrases index](https://www.chineseidioms.com/phrases).
   - **MDBG dictionary fallback** for anything not on chineseidioms.com: `https://www.mdbg.net/chinese/dictionary?wdqb=<url-encoded-hanzi>`. Universal coverage, just dictionary glosses — used as the fallback for Core / Slang rows the project couldn't match to a richer source.
   - Use `scripts/find_site_links.py` to bulk-apply: `--apply` writes chineseidioms.com matches only; `--apply --mdbg-fallback` also fills the rest with MDBG URLs. The script never overwrites an existing Link value.
10. `Tags` — space-separated tags. See tag conventions below.

The Anki note type has two additional fields that **never appear in TSV**: `Audio` (for `[sound:file.mp3]` references) and `PersonalNote` (free-form user notes added inside Anki). Because they are omitted from the `#columns:` directive, Anki preserves them untouched on every re-import.

**Hanzi (column 1) is the deck's de-facto unique key.** Anki import is set to match on first field, so re-importing a row with the same Hanzi *updates* the existing note rather than creating a duplicate.

## Workflow

The TSV files are **append-only**. Adding new vocab:

1. Append rows to the appropriate TSV (no edits to existing rows unless fixing a mistake).
2. Re-import into Anki — Anki matches by first field (Hanzi) and updates existing notes / adds new ones. The directive block tells Anki the separator, column-to-field mapping, and which column holds tags.
3. Commit.

Do not reorder existing rows. Do not strip or reorder the directive block at the top of each file.

## Tag conventions

Two kinds of tags coexist in column 10:

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

15 columns. Directive block:

```
#separator:tab
#html:true
#columns:Key	Component	Pinyin	Meaning	MemberChars	SameSyllableChars	Productivity	Frequency	Decomposition	MemberDecomp	CrossRefs	Note	Link	Audio	Tags
#tags column:15
```

1. `Key` — `<component>:<numeric-pinyin>` (e.g. `肖:qiao4`). Anki's first field must be unique per note, and the same component can produce multiple sounds (`肖` → xiāo / qiào / shāo), so `Component` alone is not unique. Card templates never display `Key` — it exists only to dedupe and to drive Anki's match-on-first-field import behavior.
2. `Component` — the lone phonetic component (e.g. `工`). Single CJK character per row.
3. `Pinyin` — the sound the component produces in derivative characters, with tone marks (e.g. `gǒng` for `工` as it appears in `巩鞏汞銾`). Note: this is the sound of the **compound**, not necessarily the component's own dictionary pronunciation. Card templates tone-color this field automatically based on the diacritic.
4. `Meaning` — English gloss from HanziCraft's dictionary (CC-CEDICT-derived), with senses ` / `-separated. Phase 2 enrichment overwrites the rough phase-1 mnemonics; if HanziCraft has no entry we fall back to whatever the source notes file had.
5. `MemberChars` — bucket 1. The set of compound characters that take this row's exact sound (matching pinyin including tone). Comes from the source's curated set; the component itself is stripped so the front of Card 2 is a real recognition test.
6. `SameSyllableChars` — bucket 2. Characters that contain this component AND share its syllable but DIFFER in tone (e.g. for `工:gōng`, this is `巩鞏汞銾` — same `gong` syllable but tone 3). Derived from HanziCraft's full member-char list (`scripts/cache/component_cwc.json`) plus per-char pinyin (`scripts/cache/char_data.json`); chars already in MemberChars are excluded. Empty when no bucket-2 chars exist.
7. `Productivity` — HanziCraft's "appears as a component in N characters" count (e.g. `121` for `工`). Total number of characters that contain this component, regardless of whether they take its sound. Card-back stat pill renders the A / B / C triple where C = Productivity, B = `len(MemberChars) + len(SameSyllableChars)`, A = `len(MemberChars)` — A: exact sound, B: same syllable any tone, C: total containing the component. The standalone "in N chars" pill was retired in phase 3D in favor of the triple.
8. `Frequency` — HanziCraft's frequency rank for the component as a standalone character (e.g. `118` for `工` being the 118th most frequent character in modern usage). Empty for rare components not in the frequency list.
9. `Decomposition` — TSV-packed top-level + radical breakdown of the component itself: `once:<a>+<b>` (top-level split, e.g. `once:一+丄` for `工`) and optionally `;radical:<r>` (canonical Kangxi radical, only when it differs from the component). Doubled-form components (e.g. `比 = 匕 + 匕`) render as `once:匕×2`. Segments are skipped entirely when HanziCraft has no usable data. Card templates parse this and render it as labeled lines on Card 1 back.
10. `MemberDecomp` — per-bucket-char once-level decomposition packed as `巩=工+凡|汞=工+水|銾=金+巠`. One entry per char in MemberChars + SameSyllableChars (skipped when HanziCraft has no usable decomp for that char). Card 2 back uses this to draw `巩 = 工 + 凡` lines under each bucket with the phonetic component highlighted.
11. `CrossRefs` — for the 33 components in the deck with multiple readings, the OTHER readings of the same component packed as `qiào / 俏峭鞘诮 · shāo / 稍梢捎艄筲`. Empty for single-reading components. Card 1 back renders this as a tone-colored "also reads" block.
12. `Note` — free-form. Used for variant/traditional forms (`Traditional: 歷`), expanded exception hints (`Exceptions (different sound): 毕昆皆毚`), related-char hints (`Also related: 位`), sound-pattern hints (`Sound pattern: always -an`), similarity warnings, and curated context from `NOTE_OVERRIDES` in the import script. Phase 3D dropped redundant single-CJK / multi-CJK "built from" tokens (info lives in Decomposition) and stat fragments (info lives in the A/B/C triple).
13. `Link` — HanziCraft URL covering the component plus all its member chars, e.g. `https://hanzicraft.com/dashboard/character/%E5%B7%A5%E5%B7%A9%E9%9E%8F%E6%B1%9E%E9%8A%BE`. Clicking opens HanziCraft's dashboard for the whole set at once. Rendered as a "HanziCraft →" footer on each card back.
14. `Audio` — `[sound:…\.mp3]` ref. Files are user-supplied; cards display fine without them, audio just no-ops until mp3s are dropped into `collection.media`.
15. `Tags` — every row has at least `phonetic-component`.

### Manual overrides

Two dicts in `scripts/import_phonetic_components.py` patch in data HanziCraft doesn't provide:

- `MEANING_OVERRIDES` — fills `Meaning` for the 7 obscure components HanziCraft has no dictionary entry for (`㐬`, `彡`, `㢆`, `尞`, `畺`, `咅`, `昷`). Applied only when HanziCraft's `definition` is empty.
- `NOTE_OVERRIDES` — appends curated context (visual-confusion warnings, productive-set quirks, etymology hints) to the `Note` of selected components. Applied to all rows of that component (i.e. all readings).

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

## Kangxi Radicals deck

`Chinese_Kangxi_Radicals.tsv` is the fifth deck. Purpose: drill recognition of the 214 traditional Kangxi semantic radicals — the meaning-bearing pieces of a Hanzi (氵 → water-themed, 心 → emotion, 钅 → metal). Pairs with the phonetic-components deck: phonetic teaches *sound*, radical teaches *meaning category*. Together they cover the phono-semantic compound model that explains ~80% of Hanzi.

### Schema

15 columns. Directive block:

```
#separator:tab
#html:true
#columns:Key	Radical	Variant1	Variant2	ReferenceVariants	Pinyin	Meaning	MemberChars	Productivity	Frequency	Decomposition	MemberDecomp	Note	Link	Tags
#tags column:15
```

1. `Key` — `<radical>:<numeric-pinyin>`. Unique first field for Anki.
2. `Radical` — canonical simplified form (single CJK char, may live in the Kangxi Radicals / Radicals Supplement Unicode blocks).
3. `Variant1` — primary positional variant. Generates its own card. E.g. for `心`: `忄` (left-side form). Empty when the radical has no major variant.
4. `Variant2` — secondary positional variant. Generates its own card. E.g. for `心`: `⺗` (bottom form). Empty when only one variant exists.
5. `ReferenceVariants` — comma-separated archaic / rare variants shown on the canonical card's back for context but with NO dedicated card. Keeps the deck card-count manageable for radicals like `网` (4 variants total — only `罒` gets its own card; rest go here).
6. `Pinyin` — tone-marked. When a radical has multiple readings (rare: `用` yòng / shuǎi), pick the primary and put the alternate in Note.
7. `Meaning` — short English gloss (`water`, `heart`, `metal`).
8. `MemberChars` — curated example characters where this radical is the *semantic head* (4-12 per row). From the seed file.
9. `Productivity` — HanziCraft's "appears as a component in N chars" count. Empty until R2 enrichment fills it.
10. `Frequency` — HanziCraft frequency rank for the radical as a standalone character. Often empty (many radicals aren't common standalone chars).
11. `Decomposition` — `once:<a>+<b>;radical:<r>` — the radical's own breakdown (same pack format as phonetic components). Filled by R2.
12. `MemberDecomp` — `海=氵+每|河=氵+可` per-member-char once-level decomp. Card 4 back highlights the radical (and its variants) in green. Filled by R2.
13. `Note` — free-form. Traditional-form mentions, alternate readings, curated context from `NOTE_OVERRIDES`.
14. `Link` — HanziCraft URL covering the radical + its member chars.
15. `Tags` — `kangxi-radical` + one tier: `radical-core` (~34 high-leverage), `radical-common` (~143 moderate), `radical-structural` (~23 simple strokes, rarely meaning-bearing), `radical-rare` (~14 archaic).

### Four card templates

Cards generated per note depend on which variant fields are populated.

- **Card 1 — Radical → Meaning** — always. Front: lone canonical radical. Back: full reveal incl. variants listing.
- **Card 2 — Variant1 → Radical+Meaning** — only when Variant1 set. Front: lone variant glyph. Back: "this is a form of X" with full meaning context.
- **Card 3 — Variant2 → Radical+Meaning** — only when Variant2 set.
- **Card 4 — Set → Radical+Meaning** — only when MemberChars set. Front: the curated semantic-head set. Back: highlight shared radical + per-member decomp lines with the radical accent-highlighted (green).

The multi-card design exists because a learner needs to recognize `忄` *separately* from `心` — seeing them together on one card lets you pass without truly knowing each form.

### Tooling

- **`scripts/import_kangxi_radicals.py`** — one-shot generator. Reads the seed `Radicals.txt`, parses the mixed-convention col-1 (sometimes simp-variant, sometimes `(pr.X)` note), hoists parens-packed variants into Variant1/2/ReferenceVariants slots, applies `VARIANT_OVERRIDES` for radicals whose source order is wrong (水: 氵 belongs before 氺), normalizes the example chars, and emits the TSV. Sort key prioritizes tier-core, then example-char count.
- **`scripts/validate_radicals.py`** — sibling of `validate_components.py`. Hard errors on empty required fields, non-CJK Radical / Variants, duplicate Keys.
- **`scripts/radicals_common.py`** — schema + `RadicalRow` dataclass + parser. Mirrors `components_common.py`.
- **`scripts/index.py`** — renders the Kangxi Radicals section, grouped by tier (core → common → structural → rare).
- **Manual override dicts** in the import script: `MEANING_OVERRIDES` (terse seed-file glosses), `NOTE_OVERRIDES` (curated context like position-specific variant notes, look-alike warnings).

The HanziCraft enrichment cache (`scripts/cache/hanzicraft.json` + `char_data.json` + `char_decomp.json`) is shared with the phonetic-components deck. R2 will fetch any radicals not yet in the cache.

## Things to NOT do

- Don't reorder rows.
- Don't add per-row novelty tags ("misc-2024-05-11") — tags should be reusable.
- Don't duplicate the same Hanzi across decks.
- Don't put example sentences in the `English` column — those go in `Examples`.
- Don't cram per-char gloss into `Note` — it has its own `Breakdown` column.
- Don't break the per-character pinyin alignment (one space-separated syllable per CJK char).
- Don't write traditional characters. Simplified only.
