# Suomen Presidentit — Deck Expansion Design

- **Date:** 2026-06-21
- **Deck:** `misc_decks/Suomen_presidentit/`
- **Status:** Approved design, pre-implementation

## 1. Goal

Expand the raw community-imported "Suomen Presidentit" CrowdAnki deck (13 notes,
2 card types) into a richer study deck: more card directions per president,
web-pulled biographical facts, and aggregate "deck-level" trivia cards. Adopt the
repo's builder convention so the deck is regenerated reproducibly from a source.

## 2. Current state

- CrowdAnki JSON at `deck.json`. One note type, 6 fields: `Ordinal`, `Name`,
  `Years`, `Image`, `Party`, `Info`. 13 notes = presidents #1 Ståhlberg → #13
  Stubb (complete, none missing).
- 2 templates: **Image→Name**, **Ordinal→Name**. `Party` / `Years` / `Info`
  appear only on the back, never quizzed.
- No builder / source file — unlike `Finland_subdivisions` and the Chinese
  provinces deck, which use `build_*.py` + `deck.source.json`.
- Data hygiene problems: `Years` carries scraped Wikipedia `<a>` links + `&nbsp;`
  + `<sup>` citations; some `Info` cells are wrapped in `<table>` tags; party
  names are inconsistent (`Kokoomuspuolue` vs `Kokoomus`, `Sosiaalidemokraatti`).

## 3. Decisions (locked with user)

| Decision | Choice |
|---|---|
| Scope | **Rich** |
| File approach | **Builder + source** (`deck.source.json` + `build_suomen_presidentit.py`) |
| Scraped HTML | **Normalize** |
| Enrichment language | **Finnish** (match the deck) |
| Aggregate set | **A** party rosters + **B** full-order recite + **C** trivia/facts. **D** (counts) dropped; **E** (events) folded into C. Order **A → B → C**. |
| B mechanism | **Single recite card, JS tap-to-reveal** |

## 4. Field schema (per-president note type)

**Existing — kept, `ord` 0–5 preserved** (so existing field ids / note guids
survive re-import): `Ordinal`, `Name`, `Years`\*, `Image`, `Party`\*, `Info`\*.

**New — appended (`ord` 6+), web-pulled, Finnish:**

- `Life` — e.g. `1867–1951`
- `Profession` — e.g. `sotilas, Suomen marsalkka`
- `Birthplace` — e.g. `Askainen`
- `KnownFor` — one line
- `Nickname` — only where a well-attested nickname exists, else empty

**New — builder-computed from `Ordinal`:**

- `Predecessor` — e.g. `Risto Ryti (5.)`; empty for #1 Ståhlberg
- `Successor` — e.g. `J. K. Paasikivi (7.)`; empty for #13 Stubb

\* normalized — see §7.

## 5. Per-president cards (14, difficulty-graded)

Order = easy recognition → hardest recall. `req` follows the repo convention
(`Finland_subdivisions`): reverse `X→Name` = `any[X]`; forward `Name→X` =
`all[X]`, so a card is skipped when its answer field is empty.

| # | Card | `req` | Tier |
|---|---|---|---|
| 1 | Image → Name | `any[Image]` | Recognize the person |
| 2 | KnownFor → Name | `any[KnownFor]` | Recognize the person |
| 3 | Nickname → Name | `any[Nickname]` | Recognize the person |
| 4 | Years → Name | `any[Years]` | Recognize the person |
| 5 | Ordinal → Name | `any[Ordinal]` | Order / position |
| 6 | Name → Ordinal | `all[Ordinal]` | Order / position |
| 7 | Name → Party | `all[Party]` | Basic facts |
| 8 | Name → KnownFor | `all[KnownFor]` | Basic facts |
| 9 | Name → Profession | `all[Profession]` | Basic facts |
| 10 | Name → Birthplace | `all[Birthplace]` | Basic facts |
| 11 | Name → Predecessor | `all[Predecessor]` | Sequence chain |
| 12 | Name → Successor | `all[Successor]` | Sequence chain |
| 13 | Name → Years | `all[Years]` | Hardest — dates |
| 14 | Name → Life | `all[Life]` | Hardest — dates |

Constraints honored: KnownFor→Name (2) precedes Name→KnownFor (8); Years→Name (4)
precedes Name→Years (13); Name→Years + Name→Life are the closing pair; Life last.

Every back renders the full profile (all fields) below the answer, in the styled
layout (§8) — so each card doubles as a review of the whole person.

## 6. Aggregate cards (deck-level)

Two new note types; notes builder-generated; every note tagged `koonti` so they
can be studied / suspended apart from the per-president set. Order **A → B → C**.

### A. Party rosters — note type "Koonti" (Basic Front/Back), 5 notes

One per normalized party. Front: `Luettele kaikki <puolue> presidentit.` Back:
ordered list with ordinals.

| Party (display) | Presidents |
|---|---|
| Kokoomus | Svinhufvud (3.), Paasikivi (7.), Niinistö (12.), Stubb (13.) |
| Sosiaalidemokraatit (SDP) | Koivisto (9.), Ahtisaari (10.), Halonen (11.) |
| Maalaisliitto (myöh. Keskusta) | Relander (2.), Kallio (4.), Kekkonen (8.) |
| Edistyspuolue | Ståhlberg (1.), Ryti (5.) |
| Sitoutumaton | Mannerheim (6.) |

Partition check: 4 + 3 + 3 + 2 + 1 = 13. ✓

### B. Full-order recite — note type "Listaus" (1 note)

Front: `Luettele Suomen presidentit järjestyksessä (1→13).` Back: a numbered 1–13
list, all names hidden; a small JS reveals **one name per tap / Space**, top to
bottom, with a "reveal all" fallback. Self-graded whole-list overview. JS kept
minimal; targets Anki desktop + AnkiDroid + AnkiMobile (user verifies in their
client — see §10).

### C. Trivia / facts — note type "Koonti" (Basic), ~10–12 notes, last

Firsts / superlatives + a few events (the folded-in "E"). Draft set (final list
confirmed during the enrichment review, §9):

- Ensimmäinen presidentti? → Ståhlberg
- Ensimmäinen naispresidentti? → Halonen
- Pisimpään istunut presidentti? → Kekkonen (n. 26 v)
- Nykyinen presidentti? → Stubb
- Kuoli virassa? → Kallio
- Erosi kesken kauden? → Ryti, Mannerheim, Kekkonen
- Poikkeuslailla valittu / kautta jatkettu? → Mannerheim, Kekkonen
- Presidentti toisen maailmansodan aikana? → Kallio, Ryti, Mannerheim
- Presidentti kun Suomi liittyi EU:hun (1995)? → Ahtisaari
- Presidentti kun Suomi liittyi Natoon (2023)? → Niinistö

## 7. Normalization rules

- **Years** → year range `YYYY–YYYY`. Died-in-office → append ` †` (Kallio).
  Current → `2024–` (Stubb). Strip every `<a>`, `&nbsp;`, `<sup>`. Exact
  start/end dates stay available in `Info` where they add value.
- **Info** → strip `<table>/<tbody>/<tr>/<td>` wrappers and `<sup>` citation
  links; keep the Finnish prose intact.
- **Party** → `PARTY_CANON` map for grouping + display:
  `Kokoomuspuolue`→`Kokoomus`, `Sosiaalidemokraatti`→`Sosiaalidemokraatit (SDP)`,
  `Maalaisliitto`/`Edistyspuolue`/`Sitoutumaton` kept as-is.

## 8. Card styling

Per-president back = a "profile" layout: `Name` (large) + `Image`, then labeled
rows (`Järjestys`, `Kausi`, `Puolue`, `Elinvuodet`, `Ammatti`, `Syntymäpaikka`,
`Tunnettu`, `Edeltäjä` / `Seuraaja`) + `Info`. Light, readable CSS extending the
deck's current minimal style. Aggregate cards: plain centered Q/A; B adds the
reveal styling/JS.

## 9. Builder mechanics — `build_suomen_presidentit.py`

Idempotent; always starts from `deck.source.json`. Steps:

1. Bootstrap (one-time, guarded): copy current `deck.json` → `deck.source.json`.
2. Load source.
3. Per note: normalize `Years` / `Info`; normalize `Party`; merge
   `ENRICH[ordinal]` (`Life`, `Profession`, `Birthplace`, `KnownFor`,
   `Nickname`); compute `Predecessor` / `Successor` from `Ordinal`.
4. Expand the per-president note model: append the new fields (fresh ids,
   existing `ord` 0–5 preserved), install the 14 templates in §5 order, rebuild
   the `ord`-indexed `req`, set the profile CSS.
5. Add note types `Koonti` + `Listaus`; generate aggregate notes (A grouped from
   `Party`, B the recite list, C the curated `TRIVIA` list).
6. Write `deck.json` (`ensure_ascii=False, indent=2, sort_keys=True`).
   `media_files` unchanged.
7. Print a summary (note counts, templates, aggregate counts).

In-script data tables: `ENRICH` (13 entries), `PARTY_CANON`, `TRIVIA`.
Enrichment values are gathered from fi/en.wikipedia and **reviewed by the user
before commit** (§9 review gate).

## 10. Risks / notes

- **Template `ord` reorder** remaps card identity in Anki. Safe here because the
  deck is freshly imported with no real review history; if it had been studied,
  the 2 original cards' history would reassign.
- **B's JS reveal** can't be verified without a real Anki client; built to the
  known incremental-reveal pattern, user verifies after import.
- **Sparsity** (`Nickname` / `Predecessor` / `Successor`) is handled by `req`, so
  no empty-prompt cards are generated.

## 11. Verification

- `python build_suomen_presidentit.py` runs clean.
- `deck.json` re-loads as JSON; 13 per-president notes intact (guids preserved);
  aggregate notes present.
- Each template's `req` matches its prompt field; no card generates with an empty
  prompt.
- Every `<img>` resolves to a file in `media/`.
- Spot-check 2–3 presidents' rendered fields (normalized `Years`, enrichment,
  pred/succ).
- Party rosters partition all 13 (4 + 3 + 3 + 2 + 1).

## 12. Out of scope

- New media / images.
- Importing into the Chinese-deck TSV pipeline (this deck stays CrowdAnki).
- `D` (counts) and standalone `E` (events) aggregate categories.
