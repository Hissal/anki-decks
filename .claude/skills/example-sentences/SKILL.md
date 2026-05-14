---
name: example-sentences
description: >
  Use when generating or sourcing example sentences for the anki-decks
  `Examples` field. Triggers on `/example-sentences`, "write examples for
  these words", "example sentences for X", or whenever the anki-import /
  anki-suggest skills need to fill `Examples`. Enforces a strict quality
  bar (modern, conversational, 5–15 chars, no literary fluff) and outputs
  ready-to-paste TSV form.
---

# example-sentences

Produce three high-quality example sentences per word/phrase, formatted
exactly the way the `Examples` TSV column expects.

## When to activate

- User invokes `/example-sentences`.
- User says "write examples for X", "give me example sentences for X",
  "examples for [Chinese words]", or similar.
- Called internally by `anki-import` and `anki-suggest` when filling the
  `Examples` column.

If a request lists multiple words, treat each independently and emit one
block per word.

## Quality bar (apply to every sentence, whether generated or sourced)

Every sentence must be:

- **Modern Mandarin**, grammatically correct, what a native speaker
  would actually say.
- **Practical** — useful in daily conversation, not literary or academic.
- **Concise but not babyish** — ideally 5–15 Chinese characters. Skip
  one-syllable trivial sentences; skip multi-clause showpieces.
- **Comprehensible** to an intermediate learner — no rare vocab piled on
  top of the target word.
- **Naturally contextualized** — the target word/phrase appears in a
  context that disambiguates its meaning.

Each sentence pairs Chinese + English. (Pinyin is rendered by the card's
ruby template from the Hanzi field; it does **not** belong in the
`Examples` column.)

### Good example (target word: 喜欢)

```
我喜欢吃中国菜。 / I like eating Chinese food.
她很喜欢看书。 / She really enjoys reading books.
你喜欢这个颜色吗？ / Do you like this color?
```

### Reject these

| Pattern | Why |
|---------|-----|
| `我喜欢你。` | Too vague, context-dependent, awkward as a teaching example. |
| `我由衷地表示对贵国文化的喜欢和敬仰。` | Literary, formal, unnatural in speech. |
| `他对古典音乐特别喜欢，并且沉浸其中不可自拔。` | Drops in rare vocab (沉浸其中, 不可自拔) that overshadows the target word. |
| `好。` | Too short, no context. |
| Sentences hand-translating English idioms into stilted Chinese. | Not natural Mandarin. |

## Output format — exact TSV form

For each word, output a single line containing three sentences separated
by literal `<br>`. Each sentence is `中文。 / English.` with one space on
each side of the `/`. This is the **canonical Examples field value** the
project's TSV ingests.

```
我喜欢吃中国菜。 / I like eating Chinese food.<br>她很喜欢看书。 / She really enjoys reading books.<br>你喜欢这个颜色吗？ / Do you like this color?
```

When responding to the user (not feeding `anki-import` directly), format
the same content as a readable block first, then show the single
TSV-ready line beneath it:

```
1. 我喜欢吃中国菜。 / I like eating Chinese food.
2. 她很喜欢看书。 / She really enjoys reading books.
3. 你喜欢这个颜色吗？ / Do you like this color?

TSV: 我喜欢吃中国菜。 / I like eating Chinese food.<br>她很喜欢看书。 / She really enjoys reading books.<br>你喜欢这个颜色吗？ / Do you like this color?
```

## Polysemy

When a word has multiple distinct senses (separated by `/` in the
`English` column), bias the three sentences to **cover the different
senses**, not three near-duplicates of one sense. E.g. for `还` (still /
again / return), produce one sentence per sense, even if it means
sacrificing one slot of "best phrasing."

For words with only one clear sense, vary subject (我/你/他/她) and
register slightly across the three sentences so the user gets distinct
practice contexts.

## External sources

You may pull example sentences from external sources rather than generate
fresh, but **filter every sourced sentence through the quality bar
above** before keeping it. Acceptable sources:

- **chineseidioms.com** — for chengyu / proverbs. The row's `Link` field
  points at the page; example sentences appear in the entry. They are
  usually fine but occasionally too literary — apply the bar.
- **tatoeba.org** — open-corpus sentence pairs. Convenient for common
  words. Many entries are bad (machine-translated, awkward, ungrammatical)
  — apply the bar harder here.
- **HSK textbook examples** — usually pedagogically clean but often dry.
  Apply the bar.

If a sourced sentence is *almost* good but breaks one rule (too long,
contains one rare word), prefer rewriting it minimally over rejecting it
outright.

Always state the source per sentence inline when responding to the user:
`(generated)`, `(chineseidioms.com)`, `(tatoeba #ID)` — so the user can
audit quality. The TSV-ready line strips these annotations.

## Red flags / refuse

Never include:

- Pinyin inside the `Examples` TSV value — pinyin is for the card's ruby
  template, not the example field.
- A `<br>` inside an individual sentence — `<br>` is the separator
  between the three sentences only.
- Romanized or simplified-to-traditional conversions of the source word —
  use the exact Hanzi from the user's input.
- A sentence that uses the target word in a register that contradicts
  the word's tier tag (e.g. don't write a casual conversational example
  for a `classical-flavor` idiom).
