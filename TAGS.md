# Tag Allowlist

Canonical list of tags used in the deck TSV files (column 6, space-separated).
The validator (`scripts/validate.py`) warns on tags that aren't listed here.
Keep this file in sync when adding genuinely new tags. Reuse existing tags
over inventing near-synonyms.

All tags are lowercase, hyphen-separated.

## Tier tags (learning priority)

Exactly one per row recommended. Drives Anki active-vs-passive study filters.

| Tag | Meaning |
|-----|---------|
| `production-ready` | High-frequency. Safe to use actively. |
| `recognition-ready` | Should recognize; occasional active use OK. |
| `recognition-first` | Recognize-only. Register-sensitive, regional, literary, dated, or low active priority. |

## Register / tone

| Tag | Meaning |
|-----|---------|
| `slang` | Casual / non-standard. |
| `old-slang` | Dated slang, still recognized. |
| `internet-slang` | Online-origin slang. |
| `dialect` | Regional flavor (Sichuan, Northeast, etc.). Not standard Mandarin. |
| `erhua` | Northern erhua-flavored form. |
| `flavor` | Stylish / characterful but not strictly slang. |
| `literary` | Written / book-flavored. |
| `classical-flavor` | Classical Chinese feel; old-fashioned. |
| `formal` | Formal register. |
| `rude-playful` | Rude but playful. Context-sensitive. |
| `tone-risky` | Can offend if misused; check context. |
| `vulgar` | Vulgar / coarse. |

## Function (how the phrase works in conversation)

| Tag | Meaning |
|-----|---------|
| `conversation-glue` | Connects, fills, smooths speech. |
| `filler` | Filler / hesitation word. |
| `connector` | Joins clauses or ideas. |
| `transition` | Shifts topic or stage. |
| `reaction` | Quick response to something heard. |
| `clarification` | Asks for or gives clarification. |
| `agreement` | Signals agreement. |
| `disagreement-softener` | Softens disagreement. |
| `opinion` | Frames an opinion. |
| `emphasis` | Adds emphasis. |
| `pattern` | Fixed grammatical pattern (e.g. `不但…而且`). |
| `contrast` | Marks contrast. |
| `summary` | Sums up. |
| `closing` | Closes a turn / conversation. |
| `greeting` | Greeting. |
| `pronunciation` | Note relates to pronunciation. |

## Domain / topic

| Tag | Meaning |
|-----|---------|
| `food` | Food and eating. |
| `health` | Health, body, fitness. |
| `culture` | General culture. |
| `culture-history` | Historical / cultural references. |
| `culture-society` | Society-and-culture cross. |
| `society` | Modern society / social phenomena. |
| `holiday` | Holidays and festivals. |
| `religion` | Religion / spirituality. |
| `education` | Education, study, school. |
| `technology` | Tech, devices, software. |
| `internet-media` | Internet platforms and media. |
| `media` | Music, film, TV, etc. |
| `nature` | Nature, weather, geography. |
| `language-learning` | Meta: words about language and learning. |
| `personality` | Personality descriptors. |
| `relationships` | Family, friends, romance. |
| `skill` | Skill, mastery. |
| `life-advice` | Wisdom / advice idioms. |
| `emotions` | Emotional state. |
| `emotions-opinions` | Emotion-laden opinion. |

## Form

| Tag | Meaning |
|-----|---------|
| `chengyu` | Four-character idiom. |
| `proverb` | Longer proverb / saying. |

## Generic catch-alls

Use sparingly — prefer a more specific tag if one fits.

| Tag | Meaning |
|-----|---------|
| `everyday-vocab` | Generic everyday word. |
| `useful-phrases` | Generic useful phrase. |

## Adding a new tag

1. Confirm no existing tag covers the meaning.
2. Add the tag here with a one-line definition in the appropriate section.
3. Use lowercase, hyphen-separated.
4. Commit `TAGS.md` together with the row that first uses it.
