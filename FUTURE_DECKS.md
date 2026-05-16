# Future deck ideas

Working list of decks that could be added on top of the existing four
(`Chinese_Core_Conversation`, `Chinese_Idioms_Proverbs_Classical`,
`Chinese_Slang_Dialect_Flavor`, `Chinese_Phonetic_Components`). Ordered roughly
by "fit with the existing stack" and "expected leverage per hour spent
building".

Each entry is a one-shot idea, not a commitment.

---

## High-leverage / strongest pairings

### Kangxi semantic radicals (active — see `~/.claude/plans/<radicals plan>`)

Completes the phono-semantic compound model. Phonetic components tell you
how a character sounds; semantic radicals tell you what category it means
(氵 → water-themed, 心 → emotion, 钅 → metal). 214 traditional Kangxi
radicals, but only ~120-150 are actually productive in modern usage. Reuses
the HanziCraft cache pipeline + the 16-col schema pattern from phonetic
components. Active plan exists.

### Measure words / 量词

Big pain point for English speakers. Card front: classifier. Card back: what
categories of nouns it counts + 2-3 concrete examples.

- `张` → flat things (纸, 票, 桌子)
- `条` → long thin things (鱼, 路, 裤子, 龙)
- `把` → things with handles (伞, 椅子, 刀)
- `只` → animals + paired items (猫, 鞋, 手)
- `件` → clothing + abstract matters (衣服, 事情)
- `本` → bound things (书, 杂志, 字典)
- `杯` → cups of liquid (水, 咖啡)
- `辆` → wheeled vehicles (车, 自行车)
- `位` → polite person counter
- `个` → catch-all (when you don't know which to use)

~40-60 high-frequency entries. Compact deck, immediate practical payoff.

### Function-word disambiguation

Notorious confusion clusters. Card front: minimal-pair sentence with the
function word blanked. Back: which particle fits + why.

Pain clusters:

- **了 (perfective vs modal/state-change)** — `吃了 vs 吃过 vs 在吃`
- **的 / 地 / 得** — attributive / adverbial / verbal-complement particle
  (all pronounced `de`)
- **着** — durative aspect (`坐着, 拿着, 看着`)
- **过** — experiential aspect (`去过, 试过`)
- **把 vs 被** — disposal vs passive
- **就 vs 才** — "soon/then" vs "only just"
- **再 vs 又** — "again in future" vs "again in past"

~30-40 entries covering most pain. Could be subdivided per cluster as tags
(`function-le`, `function-de`, etc.).

---

## Fun stuff (parallel to slang/idioms decks)

### Onomatopoeia / 拟声词

Adds texture, sticks in memory because sounds are evocative. Tags:
`onomatopoeia`, `flavor`.

- `哗啦` — splashing/rustling
- `咕咚` — heavy thud / gulp
- `嗒嗒` — clicking / tapping
- `噼里啪啦` — crackling / chain of small sounds
- `叮咚` — doorbell ding-dong
- `呼呼` — wind / snoring
- `叽叽喳喳` — chirping / chatter
- `咯咯` — clucking / giggling
- `呜呜` — sobbing / wailing
- `轰隆` — rumbling thunder / explosion

~30-50 entries. Fits the "flavor deck" vibe.

### Internet abbreviations / 网络缩写

Modern register, fast-evolving. Pairs with the slang deck. Often
pinyin-initials or Cantonese-influenced.

- `yyds` — 永远的神 ("eternal god" — GOAT)
- `xswl` — 笑死我了 (lol/dying)
- `666` — well done / impressive (homophone of 溜溜溜)
- `juejuezi` / 绝绝子 — amazing/awful (sarcastic)
- `awsl` — 啊我死了 ("ah I'm dead" — cuteness overload)
- `bdjw` — 不懂就问 (asking honestly)
- `dbq` — 对不起 (sorry)
- `xdm` — 兄弟们 (bros)
- `nbcs` — nobody cares
- `yysy` — 有一说一 (to be fair)

~20-40 high-currency entries. Re-curate periodically as slang shifts.

---

## Mid-priority / nice-to-haves

### Sentence patterns / 句型

`把字句`, `越来越...`, `不但...而且...`, `一边...一边...`, `连...都...`,
`无论...都...`. ~50 patterns. Card front: skeleton with blanks. Back: filled
example + register note.

### Common 2-char compounds / collocations

Productive 词组 not in Core (verb-object pairs like 打电话, 唱歌, 上网,
洗澡). Could overlap with Core; works better as a focused HSK-graded
expansion list.

### Tone-pair minimal pairs

Audio-focused. 买 (mǎi) vs 卖 (mài), 妈 (mā) vs 麻 (má) vs 马 (mǎ) vs 骂
(mà), 西 (xī) vs 习 (xí). Drills tonal discrimination for listening.
Niche — assumes audio files curated.

### Hanzi visual look-alikes

Standalone "spot the difference" deck for notoriously similar characters.
己/已/巳, 千/干/壬, 末/未/朱, 戊/戌/戍/戎, 由/甲/申/田, 大/太/犬,
夫/天/失. Card front: cluster of look-alikes. Back: how to distinguish +
sample words. ~30-50 clusters.

### Chengyu with stories / 成语故事

Extension of the idioms deck — picks 30-50 of the most famous chengyu and
adds a one-sentence story snippet on the back (画蛇添足 → mention the
overzealous painter who lost the wager).

---

## Lower-priority / specialized

### Numbers, dates, times

Practical but covered well by textbooks. Low Anki value.

### Place names / 地名

If/when the user starts traveling specific regions.

### Business Chinese / formal register

Domain-specific; defer until needed.

### Stroke-order training

Different from reading focus — better served by handwriting apps (Skritter,
hanzigrid) than Anki cards.

### Pinyin spelling drills

For typing input correctness. Niche.
