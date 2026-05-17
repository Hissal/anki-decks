# Context + Hint Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two optional fields (`Context` + `Hint`) to the word-deck schema and note type, surfacing them on Anki cards per the design at `docs/superpowers/specs/2026-05-17-context-and-hint-fields-design.md`.

**Architecture:** Schema bumps 8 → 10 cols across all three word-deck TSVs. Two new fields slot between `Note` and `Link`. A one-shot Python migration script appends two empty trailing tabs to every existing row in one go. A new pure-JS helper `parseHint(text, cardType)` lives in `_ruby.js` and is used by both fronts (click-to-reveal button) and backs (auto-revealed labeled line). Templates wire the helper via `data-hint` + `data-card-type` + optional `data-revealed` attributes on mount elements.

**Tech Stack:** Python 3 (deck tooling), vanilla JS in Anki templates (no build step), HTML/CSS for cards, TSV for data files. Test infra: stdlib `assert` for Python checks, Node's built-in `assert` module for JS parser tests (no Node test framework).

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `scripts/common.py` | Modify | Schema constants (`EXPECTED_HEADER`, `COLUMN_COUNT`), `Row` dataclass, `parse_tsv()` field mapping |
| `scripts/validate.py` | Modify | New validation rules for `Context` and `Hint` |
| `scripts/append_empty_cols.py` | Create + delete | One-shot migration: bumps `#columns:` + `#tags column:` directives, appends `\t\t` per row, in all three word-deck TSVs |
| `Chinese_Core_Conversation.tsv` | Modify (migration) | Directive header + every row gains 2 empty trailing tabs |
| `Chinese_Idioms_Proverbs_Classical.tsv` | Modify (migration) | Same |
| `Chinese_Slang_Dialect_Flavor.tsv` | Modify (migration) | Same |
| `note_type/Chinese_anki_decks/_ruby.js` | Modify | Add `parseHint()` + `mountHint()`; export via `window.ankiDecks` |
| `note_type/Chinese_anki_decks/_ruby.test.js` | Create | Node-runnable assertion tests for `parseHint` |
| `note_type/Chinese_anki_decks/styles.css` | Modify | New `.context-prompt`, `.hint-revealed`, `.hint-label` classes |
| `note_type/Chinese_anki_decks/production_front.html` | Modify | Add Context line + Hint mount |
| `note_type/Chinese_anki_decks/production_back.html` | Modify | Add Context line + Hint mount (`data-revealed="true"`) |
| `note_type/Chinese_anki_decks/hanzi_recognition_front.html` | Modify | Add Hint mount |
| `note_type/Chinese_anki_decks/hanzi_recognition_back.html` | Modify | Add Context line + Hint mount (`data-revealed="true"`) |
| `note_type/Chinese_anki_decks/audio_recognition_front.html` | Modify | Add Hint mount |
| `note_type/Chinese_anki_decks/audio_recognition_back.html` | Modify | Add Context line + Hint mount (`data-revealed="true"`) |
| `note_type/Chinese_anki_decks/README.md` | Modify | Update install field list, document Hint format |
| `scripts/index.py` | Modify | Render Context next to English in word-deck entries |
| `CLAUDE.md` | Modify | Bump schema docs to 10 columns, document Context + Hint |

---

## Task 1: Schema bump in `common.py`

**Files:**
- Modify: `scripts/common.py:13-23` (EXPECTED_HEADER + COLUMN_COUNT)
- Modify: `scripts/common.py:48-63` (`Row` dataclass)
- Modify: `scripts/common.py:120-133` (`parse_tsv` field mapping)

- [ ] **Step 1: Update `EXPECTED_HEADER`**

Replace lines 13-22 with the new 10-column header:

```python
EXPECTED_HEADER = [
    "Hanzi",
    "Pinyin",
    "English",
    "Breakdown",
    "Examples",
    "Note",
    "Context",
    "Hint",
    "Link",
    "Tags",
]
```

`COLUMN_COUNT = len(EXPECTED_HEADER)` on line 23 picks up the new value automatically. `EXPECTED_DIRECTIVES["tags column"]` is built from `str(COLUMN_COUNT)` on line 30 and updates automatically too.

- [ ] **Step 2: Add Context + Hint to `Row` dataclass**

In `scripts/common.py` replace the `Row` dataclass (lines 48-63) with:

```python
@dataclass
class Row:
    file: Path
    line_no: int  # 1-indexed file line number
    hanzi: str
    pinyin: str
    english: str
    breakdown: str
    examples: str
    note: str
    context: str
    hint: str
    link: str
    tags: list[str] = field(default_factory=list)

    @property
    def raw_tags(self) -> str:
        return " ".join(self.tags)
```

Order matches the new `EXPECTED_HEADER`. `tags` stays last because it's the only field with a default value (`field(default_factory=list)` — must come after non-default fields).

- [ ] **Step 3: Update `parse_tsv` field mapping**

In `scripts/common.py` replace the `rows.append(Row(...))` block (lines 120-133) with:

```python
        rows.append(
            Row(
                file=path,
                line_no=i,
                hanzi=fields[0],
                pinyin=fields[1],
                english=fields[2],
                breakdown=fields[3],
                examples=fields[4],
                note=fields[5],
                context=fields[6],
                hint=fields[7],
                link=fields[8],
                tags=[t for t in fields[9].split(" ") if t],
            )
        )
```

- [ ] **Step 4: Verify common.py syntax**

Run: `python -c "from scripts.common import EXPECTED_HEADER, COLUMN_COUNT, Row; print(COLUMN_COUNT, EXPECTED_HEADER)"`

Expected: `10 ['Hanzi', 'Pinyin', 'English', 'Breakdown', 'Examples', 'Note', 'Context', 'Hint', 'Link', 'Tags']`

Do NOT commit yet — the existing TSVs are still 8-column and will fail validation. Migration happens in Task 3 and the whole batch lands in one commit at Task 4.

---

## Task 2: Validator rules for Context + Hint

**Files:**
- Modify: `scripts/common.py` (add `HINT_CARD_TYPES` + `HINT_PREFIX_RE`)
- Modify: `scripts/validate.py` (import helpers; add Context + Hint validation pass)

- [ ] **Step 1: Add the constants to `common.py`**

In `scripts/common.py`, after the existing regex definitions (after the `DIGIT_TONE_RE = ...` line at line 167), append:

```python
# Hint format: each <br>-separated line may start with "<card-type>:" to scope
# it to one card. parseHint() in _ruby.js mirrors these constants.
HINT_CARD_TYPES = {"hanzi", "audio", "production"}
HINT_PREFIX_RE = re.compile(r"^([A-Za-z][A-Za-z_]*)\s*:\s*(.+)$")
```

- [ ] **Step 2: Import the new helpers in `validate.py`**

At the top of `scripts/validate.py`, replace the existing `from common import (...)` block (around lines 31-43) with:

```python
from common import (
    COLUMN_COUNT,
    EXPECTED_HEADER,
    HAN_RE,
    HINT_CARD_TYPES,
    HINT_PREFIX_RE,
    TIER_TAGS,
    deck_paths,
    has_ascii_letter,
    has_han,
    load_allowed_tags,
    looks_like_digit_pinyin,
    parse_tsv,
    stderr,
)
```

- [ ] **Step 3: Add `Context` + `Hint` validation rules**

In `scripts/validate.py`, just before the `# Tag checks.` block (around line 137), insert:

```python
            # Context / Hint length warnings (terse fields).
            if r.context and len(r.context) > 120:
                warnings.append(
                    f"{loc}: Context is {len(r.context)} chars; consider keeping it terse (≤120)"
                )
            if r.hint and len(r.hint) > 120:
                warnings.append(
                    f"{loc}: Hint is {len(r.hint)} chars; consider keeping it terse per line (≤120)"
                )

            # Hint prefix sanity: warn on prefixes that look like card-type tags
            # but aren't in {hanzi, audio, production}. Catches typos like
            # "prod:" or "production_card:".
            if r.hint:
                for raw_line in r.hint.split("<br>"):
                    line = raw_line.strip()
                    m = HINT_PREFIX_RE.match(line)
                    if m and m.group(1).lower() not in HINT_CARD_TYPES:
                        warnings.append(
                            f"{loc}: Hint line starts with unrecognized prefix "
                            f"{m.group(1)!r}: (expected one of {sorted(HINT_CARD_TYPES)}); "
                            f"will render as universal"
                        )
```

- [ ] **Step 4: Verify common.py + validate.py syntax**

Run: `python -c "import sys; sys.path.insert(0, 'scripts'); from common import HINT_CARD_TYPES, HINT_PREFIX_RE; from validate import main; print('ok', HINT_CARD_TYPES)"`

Expected: `ok {'hanzi', 'audio', 'production'}` (order may vary — it's a set).

If this errors, the imports are wrong — fix before continuing. Do NOT run the validator yet (TSVs still 8-col).

---

## Task 3: One-shot migration script

**Files:**
- Create: `scripts/append_empty_cols.py`

- [ ] **Step 1: Write the migration script**

Create `scripts/append_empty_cols.py` with the full contents:

```python
#!/usr/bin/env python3
"""One-shot migration: bump word-deck TSVs from 8 columns to 10.

For each word-deck TSV in the repo root:
  - rewrite the `#columns:` directive to include Context + Hint
  - rewrite `#tags column:` to point at column 10
  - append two empty trailing tabs to every non-directive, non-blank data row

Existing column data is preserved untouched; only the directive header and per-row
column widths change. Designed to be run exactly once, then deleted.

Usage:
  python scripts/append_empty_cols.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WORD_DECK_FILES = [
    "Chinese_Core_Conversation.tsv",
    "Chinese_Idioms_Proverbs_Classical.tsv",
    "Chinese_Slang_Dialect_Flavor.tsv",
]

OLD_COLUMNS_DIRECTIVE = (
    "#columns:Hanzi\tPinyin\tEnglish\tBreakdown\tExamples\tNote\tLink\tTags"
)
NEW_COLUMNS_DIRECTIVE = (
    "#columns:Hanzi\tPinyin\tEnglish\tBreakdown\tExamples\tNote\tContext\tHint\tLink\tTags"
)
OLD_TAGS_COLUMN_DIRECTIVE = "#tags column:8"
NEW_TAGS_COLUMN_DIRECTIVE = "#tags column:10"


def migrate(path: Path) -> tuple[int, int]:
    """Return (rows_padded, lines_total)."""
    text = path.read_text(encoding="utf-8")
    # Detect line ending.
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)
    if lines and lines[-1] == "":
        # Preserve trailing newline by remembering and re-adding.
        trailing_blank = True
        lines.pop()
    else:
        trailing_blank = False

    rows_padded = 0
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == OLD_COLUMNS_DIRECTIVE:
            out.append(NEW_COLUMNS_DIRECTIVE)
        elif stripped == OLD_TAGS_COLUMN_DIRECTIVE:
            out.append(NEW_TAGS_COLUMN_DIRECTIVE)
        elif not stripped or stripped.startswith("#"):
            out.append(line)
        else:
            # Data row. Verify it has the expected old column count, then pad.
            cols = line.split("\t")
            if len(cols) != 8:
                raise SystemExit(
                    f"{path.name}: row has {len(cols)} cols, expected 8 — abort. "
                    f"Line: {line[:80]!r}"
                )
            # Insert two empty cols BETWEEN Note (idx 5) and Link (idx 6) so
            # column order matches the new schema: Note Context Hint Link Tags.
            new_cols = cols[:6] + ["", ""] + cols[6:]
            out.append("\t".join(new_cols))
            rows_padded += 1

    final = eol.join(out)
    if trailing_blank:
        final += eol
    path.write_text(final, encoding="utf-8", newline="")
    return rows_padded, len(lines)


def main() -> int:
    for name in WORD_DECK_FILES:
        path = REPO_ROOT / name
        if not path.exists():
            print(f"skip: {name} (not found)")
            continue
        rows_padded, total = migrate(path)
        print(f"{name}: padded {rows_padded} data rows ({total} total lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

The critical detail: empty columns get **inserted between Note and Link** (after index 5, before index 6), not appended at the end. Otherwise the existing `Tags` field would shift from col 8 to col 10 incorrectly. The migration script preserves Tags as the last column.

- [ ] **Step 2: Dry-run the migration on one file**

Run: `python -c "from scripts.append_empty_cols import migrate; from pathlib import Path; p = Path('Chinese_Slang_Dialect_Flavor.tsv'); print(migrate(p))"`

Expected output: a tuple like `(N, M)` where N is the number of data rows padded.

- [ ] **Step 3: Verify the file is now 10-col**

Run: `python -c "p = open('Chinese_Slang_Dialect_Flavor.tsv', encoding='utf-8'); [print(repr(line)) for line in p.readlines()[:5]]"`

Expected: first 5 lines show 4 directive lines (now with the new 10-column `#columns` + `tags column:10`) plus one data row with 9 tab-separated values (10 columns = 9 tabs).

Visually verify the migrated row preserves all original content and has two empty columns inserted between the original Note and Link positions.

- [ ] **Step 4: Reset the slang file and migrate all three together**

The dry-run in Step 2 already migrated the slang file. Reset it so the full migration runs against all three files in a clean state:

```bash
git restore Chinese_Slang_Dialect_Flavor.tsv
```

Then run the full migration:

```bash
python scripts/append_empty_cols.py
```

Expected output: three lines, one per file, each reporting `padded N data rows (...)` with N matching the row count of that deck.

- [ ] **Step 5: Verify all three TSVs are 10-col**

Run for each file:
```bash
python -c "import sys; p = open(sys.argv[1], encoding='utf-8'); lines = p.readlines(); data = [l for l in lines if l.strip() and not l.startswith('#')]; print(sys.argv[1], 'cols on first data row:', data[0].rstrip('\n').count('\t') + 1)" Chinese_Core_Conversation.tsv
```

Repeat for `Chinese_Idioms_Proverbs_Classical.tsv` and `Chinese_Slang_Dialect_Flavor.tsv`.

Expected: each prints `... cols on first data row: 10`.

- [ ] **Step 6: Run validator**

Run: `python scripts/validate.py`

Expected: zero errors. Warnings on existing untagged or non-tier-tagged rows are pre-existing and unrelated.

---

## Task 4: Commit the schema migration

**Files:**
- Stage: `scripts/common.py`, `scripts/validate.py`, all 3 TSVs
- Delete (do not stage): `scripts/append_empty_cols.py`

- [ ] **Step 1: Delete the throwaway migration script**

```bash
rm scripts/append_empty_cols.py
```

- [ ] **Step 2: Stage + commit**

```bash
git add scripts/common.py scripts/validate.py Chinese_Core_Conversation.tsv Chinese_Idioms_Proverbs_Classical.tsv Chinese_Slang_Dialect_Flavor.tsv
git status
```

Verify nothing else is staged and no untracked migration script remains. Then:

```bash
git commit -m "feat: word-deck schema 8 → 10 cols (add Context + Hint)

Two new optional fields slot between Note and Link in all three word
decks (Core / Idioms / Slang). Context: terse disambiguator (e.g.
'northeastern slang') so the production prompt is answerable without
seeing the back. Hint: optional click-to-reveal clue with per-card
prefix format (hanzi:/audio:/production:) for card-specific variants.

All existing rows migrate to empty Context + Hint values with zero data
loss. Validator enforces the new schema and warns on long values or
typo'd Hint prefixes."
```

- [ ] **Step 3: Verify validator still clean post-commit**

Run: `python scripts/validate.py`

Expected: zero errors.

---

## Task 5: `parseHint()` JS function with tests

**Files:**
- Modify: `note_type/Chinese_anki_decks/_ruby.js` (add `parseHint` private function + expose)
- Create: `note_type/Chinese_anki_decks/_ruby.test.js`

- [ ] **Step 1: Write failing tests**

Create `note_type/Chinese_anki_decks/_ruby.test.js` with:

```js
/*
 * Node-runnable tests for the pure JS helpers in _ruby.js.
 *
 * The Anki template loads _ruby.js as a <script> tag and the helpers attach
 * to window.ankiDecks. To make them testable in Node we duplicate the
 * minimal needed surface via a thin loader: read _ruby.js, eval inside a
 * fake `window` global, then read the helpers off it.
 *
 * Run: node note_type/Chinese_anki_decks/_ruby.test.js
 */

"use strict";

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const vm = require("vm");

const src = fs.readFileSync(path.join(__dirname, "_ruby.js"), "utf-8");
const sandbox = {
  window: {},
  document: { addEventListener: () => {} },
  console: console,
};
vm.createContext(sandbox);
vm.runInContext(src, sandbox);

const { parseHint } = sandbox.window.ankiDecks;
assert.ok(typeof parseHint === "function", "parseHint must be exported on window.ankiDecks");

// --- parseHint cases ---

// Universal (no prefix): every card type sees the same content.
assert.strictEqual(parseHint("doubled syllable + 的", "hanzi"), "doubled syllable + 的");
assert.strictEqual(parseHint("doubled syllable + 的", "audio"), "doubled syllable + 的");
assert.strictEqual(parseHint("doubled syllable + 的", "production"), "doubled syllable + 的");

// Per-card prefix: only the matching card sees the line.
const perCard = "hanzi: starts with 杠<br>audio: doubled syllable<br>production: northeastern flavor";
assert.strictEqual(parseHint(perCard, "hanzi"), "starts with 杠");
assert.strictEqual(parseHint(perCard, "audio"), "doubled syllable");
assert.strictEqual(parseHint(perCard, "production"), "northeastern flavor");

// Universal + per-card mix: matching card gets both.
const mixed = "northeastern slang<br>audio: doubled syllable";
assert.strictEqual(parseHint(mixed, "hanzi"), "northeastern slang");
assert.strictEqual(parseHint(mixed, "audio"), "northeastern slang<br>doubled syllable");
assert.strictEqual(parseHint(mixed, "production"), "northeastern slang");

// Case insensitive prefix.
assert.strictEqual(parseHint("Production: capitalized", "production"), "capitalized");
assert.strictEqual(parseHint("HANZI: shouty", "hanzi"), "shouty");

// Whitespace around prefix.
assert.strictEqual(parseHint("hanzi  :   spaced", "hanzi"), "spaced");

// Unrecognized prefix → kept as universal (treated as content).
assert.strictEqual(parseHint("note: keep this", "hanzi"), "note: keep this");

// Empty input → empty output.
assert.strictEqual(parseHint("", "production"), "");
assert.strictEqual(parseHint(null, "production"), "");
assert.strictEqual(parseHint(undefined, "production"), "");

// All lines tagged for other cards → empty.
assert.strictEqual(parseHint("hanzi: a<br>audio: b", "production"), "");

// <br /> and <br/> variants split correctly.
assert.strictEqual(parseHint("one<br/>two<br />three", "hanzi"), "one<br>two<br>three");

console.log("parseHint: all tests passed");
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `node note_type/Chinese_anki_decks/_ruby.test.js`

Expected: error about `parseHint must be exported on window.ankiDecks` because the function doesn't exist yet.

- [ ] **Step 3: Implement `parseHint`**

In `note_type/Chinese_anki_decks/_ruby.js`, inside the existing IIFE, add the function after `mountExamples` (around line 130, before `_makeAudio`):

```js
  // Hint format spec: each <br>-separated line may begin with "<card-type>:"
  // (case-insensitive, optional whitespace around the colon) to scope it to
  // one card. Recognized card types are hanzi / audio / production.
  // Mirrors HINT_CARD_TYPES + HINT_PREFIX_RE in scripts/common.py.
  var HINT_CARD_TYPES = { hanzi: 1, audio: 1, production: 1 };
  var HINT_PREFIX_RE = /^([A-Za-z][A-Za-z_]*)\s*:\s*(.+)$/;

  function parseHint(text, cardType) {
    if (!text) return "";
    var lines = String(text).split(/<br\s*\/?>/i);
    var kept = [];
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim();
      if (!line) continue;
      var m = HINT_PREFIX_RE.exec(line);
      if (m && HINT_CARD_TYPES.hasOwnProperty(m[1].toLowerCase())) {
        if (m[1].toLowerCase() === cardType) {
          kept.push(m[2].trim());
        }
        // else: line is scoped to a different card; drop it.
      } else {
        kept.push(line);
      }
    }
    return kept.join("<br>");
  }
```

- [ ] **Step 4: Export `parseHint` on `window.ankiDecks`**

In `_ruby.js`, replace the existing `window.ankiDecks = { ... };` block (line 232-238) with:

```js
  window.ankiDecks = {
    mountRuby: mountRuby,
    attachToggle: attachToggle,
    mountExamples: mountExamples,
    attachAudioButton: attachAudioButton,
    mountAutoplayAudio: mountAutoplayAudio,
    parseHint: parseHint,
  };
```

- [ ] **Step 5: Re-run tests — expect PASS**

Run: `node note_type/Chinese_anki_decks/_ruby.test.js`

Expected: `parseHint: all tests passed`.

- [ ] **Step 6: Commit**

```bash
git add note_type/Chinese_anki_decks/_ruby.js note_type/Chinese_anki_decks/_ruby.test.js
git commit -m "feat: parseHint() for per-card Hint format

Splits a Hint field on <br>, filters by an optional 'hanzi:' / 'audio:'
/ 'production:' prefix on each line, returns the joined kept lines.
Lines with no recognized prefix render on every card (universal). Lines
with a recognized prefix render only on the matching card.

Includes Node-runnable test harness (no test framework dependency)
that loads _ruby.js into a vm sandbox and asserts on the exported
function."
```

---

## Task 6: `mountHint()` and DOM wiring

**Files:**
- Modify: `note_type/Chinese_anki_decks/_ruby.js` (add `mountHint`, export)

- [ ] **Step 1: Add `mountHint` function**

In `_ruby.js`, immediately after the `parseHint` function from Task 5, add:

```js
  function mountHint(selector) {
    var nodes = document.querySelectorAll(selector);
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.dataset.ankiHintMounted === "1") continue;
      el.dataset.ankiHintMounted = "1";

      var cardType = (el.dataset.cardType || "").toLowerCase();
      var rawHint = el.dataset.hint || "";
      var parsed = parseHint(rawHint, cardType);
      if (!parsed) {
        // Empty after filtering → no UI. Conditional templates already collapse
        // when Hint is empty, but per-card filtering can also yield empty.
        el.style.display = "none";
        continue;
      }

      var revealed = el.dataset.revealed === "true";
      if (revealed) {
        el.classList.add("hint-revealed");
        el.innerHTML =
          '<span class="hint-label">Hint:</span> ' +
          '<span class="hint-text">' + parsed + '</span>';
      } else {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "hint-btn";
        btn.textContent = "Show hint";
        (function (e, p) {
          btn.addEventListener("click", function () {
            e.classList.add("hint-revealed");
            e.innerHTML =
              '<span class="hint-label">Hint:</span> ' +
              '<span class="hint-text">' + p + '</span>';
          });
        })(el, parsed);
        el.appendChild(btn);
      }
    }
  }
```

- [ ] **Step 2: Export `mountHint`**

Update the `window.ankiDecks` block in `_ruby.js` to include `mountHint`:

```js
  window.ankiDecks = {
    mountRuby: mountRuby,
    attachToggle: attachToggle,
    mountExamples: mountExamples,
    attachAudioButton: attachAudioButton,
    mountAutoplayAudio: mountAutoplayAudio,
    parseHint: parseHint,
    mountHint: mountHint,
  };
```

- [ ] **Step 3: Verify `_ruby.test.js` still passes**

Run: `node note_type/Chinese_anki_decks/_ruby.test.js`

Expected: `parseHint: all tests passed`. (We don't add tests for `mountHint` because it requires a DOM; verified manually in Anki at Task 13.)

- [ ] **Step 4: Commit**

```bash
git add note_type/Chinese_anki_decks/_ruby.js
git commit -m "feat: mountHint() — DOM wiring for Hint render

Reads data-hint + data-card-type from a mount element, parses via
parseHint(), renders either a click-to-reveal 'Show hint' button (when
data-revealed is absent) or an inline labeled 'Hint: …' line (when
data-revealed='true' for back-side mounts).

Idempotent via data-ankiHintMounted='1' guard so re-renders are safe.
Hides the mount entirely when the parsed result is empty so the layout
collapses cleanly on cards where the hint targets a different card type."
```

---

## Task 7: CSS for Context + Hint

**Files:**
- Modify: `note_type/Chinese_anki_decks/styles.css`

- [ ] **Step 1: Add the new style rules**

Append to `note_type/Chinese_anki_decks/styles.css`:

```css
/* ---------- Context + Hint (Task: Context+Hint fields) ---------- */

.context-prompt {
  font-size: 14px;
  color: #6b7280;
  font-style: italic;
  text-align: center;
  margin: 0 0 12px 0;
  letter-spacing: 0.02em;
}

.night_mode .context-prompt,
.nightMode .context-prompt { color: #9ca3af; }

/* On backs, Context renders inline above .note with a small label. */
.context-back {
  font-size: 14px;
  color: #4b5563;
  margin: 14px auto 6px;
  max-width: 560px;
  text-align: left;
  line-height: 1.6;
}

.context-back .context-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
  margin-right: 6px;
}

.night_mode .context-back,
.nightMode .context-back { color: #b8b8b8; }
.night_mode .context-back .context-label,
.nightMode .context-back .context-label { color: #9ca3af; }

/* Hint mount: button on fronts, labeled line on backs. */
.hint-mount {
  display: block;
  margin: 16px auto 0;
  text-align: center;
}

.hint-revealed {
  font-size: 14px;
  color: #4b5563;
  margin: 12px auto;
  max-width: 560px;
  line-height: 1.6;
}

.hint-revealed .hint-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
  margin-right: 6px;
}

.night_mode .hint-revealed,
.nightMode .hint-revealed { color: #b8b8b8; }
.night_mode .hint-revealed .hint-label,
.nightMode .hint-revealed .hint-label { color: #9ca3af; }
```

- [ ] **Step 2: Commit**

```bash
git add note_type/Chinese_anki_decks/styles.css
git commit -m "style: add .context-prompt, .context-back, .hint-mount, .hint-revealed

Mirrors the muted-grey-italic treatment of .note/.english-prompt for
visual cohesion. Context lives above the English prompt on the
production front (.context-prompt) and as a labeled line on backs
(.context-back). Hint reveals to a similar labeled line via .hint-revealed.

Reuses .hint-btn unchanged for the front-side reveal button."
```

---

## Task 8: Production card templates

**Files:**
- Modify: `note_type/Chinese_anki_decks/production_front.html`
- Modify: `note_type/Chinese_anki_decks/production_back.html`

- [ ] **Step 1: Rewrite production front**

Replace the entire contents of `note_type/Chinese_anki_decks/production_front.html` with:

```html
<!-- Card 3 front: Production (English → Hanzi). Context (when set) above
     the English prompt; Hint (when non-empty after parseHint) as a
     click-to-reveal button below. -->

<div class="card-side card-front">
  {{#Context}}
  <div class="context-prompt">{{Context}}</div>
  {{/Context}}

  <div class="english-prompt">{{English}}</div>

  {{#Hint}}
  <div class="hint-mount"
       data-hint="{{text:Hint}}"
       data-card-type="production"></div>
  {{/Hint}}
</div>

<script src="_ruby.js"></script>
<script>
  (function () { window.ankiDecks.mountHint(".hint-mount"); })();
</script>
```

`{{text:Hint}}` is Anki's text filter which strips HTML escaping — necessary because the field stores literal `<br>` separators (deck is `#html:true`) and we want them as text for the JS parser, not as rendered HTML.

- [ ] **Step 2: Update production back**

In `note_type/Chinese_anki_decks/production_back.html`, insert the Context block right before the `{{#Note}}` block (around line 26), and add a Hint mount after `{{#Note}}`/`{{#PersonalNote}}`. The full back becomes:

```html
<!-- Card 3 back: Production. Full reveal — replays audio via the custom
     mount so the addon's volume slider applies. -->

<div class="card-side card-back">
  <div class="hanzi-block show-all-ruby"
       id="hanzi-block"
       data-hanzi="{{text:Hanzi}}"
       data-pinyin="{{text:Pinyin}}"></div>
  <button class="toggle-btn" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

  <div class="audio-mount" data-soundfile="{{soundfile:Audio}}"></div>

  <hr>

  <div class="english">{{English}}</div>

  {{#Breakdown}}
  <div class="breakdown">{{Breakdown}}</div>
  {{/Breakdown}}

  {{#Examples}}
  <div class="examples-raw" hidden>{{Examples}}</div>
  <div class="examples"></div>
  {{/Examples}}

  {{#Context}}
  <div class="context-back">
    <span class="context-label">Context:</span>{{Context}}
  </div>
  {{/Context}}

  {{#Note}}
  <div class="note">{{Note}}</div>
  {{/Note}}

  {{#Hint}}
  <div class="hint-mount"
       data-hint="{{text:Hint}}"
       data-card-type="production"
       data-revealed="true"></div>
  {{/Hint}}

  {{#PersonalNote}}
  <div class="personal-note">{{PersonalNote}}</div>
  {{/PersonalNote}}

  {{#Link}}
  <div class="link-footer"><a href="{{Link}}" target="_blank" rel="noopener">Read more →</a></div>
  {{/Link}}
</div>

<script src="_ruby.js"></script>
<script>
  (function () {
    window.ankiDecks.mountRuby("hanzi-block", { revealed: true });
    window.ankiDecks.attachToggle("hanzi-block", "toggle-pinyin-btn");
    window.ankiDecks.mountAutoplayAudio(".audio-mount");

    var raw = document.querySelector(".examples-raw");
    var target = document.querySelector(".examples");
    if (raw && target) {
      target.innerHTML = raw.innerHTML;
      raw.remove();
      window.ankiDecks.mountExamples(".examples");
    }

    window.ankiDecks.mountHint(".hint-mount");
  })();
</script>
```

- [ ] **Step 3: Commit**

```bash
git add note_type/Chinese_anki_decks/production_front.html note_type/Chinese_anki_decks/production_back.html
git commit -m "feat: production card — Context above English, Hint below

Front: Context renders as a small muted italic line above the English
prompt when populated. Hint mounts as a click-to-reveal button below.

Back: Context renders as a labeled line above the Note section. Hint
mounts auto-revealed (data-revealed='true') as a labeled line between
Note and PersonalNote."
```

---

## Task 9: Hanzi-recognition card templates

**Files:**
- Modify: `note_type/Chinese_anki_decks/hanzi_recognition_front.html`
- Modify: `note_type/Chinese_anki_decks/hanzi_recognition_back.html`

- [ ] **Step 1: Add Hint mount to hanzi-recognition front**

In `note_type/Chinese_anki_decks/hanzi_recognition_front.html`, insert the Hint mount inside the `<div class="card-side card-front">` block after the play-audio button, and add `mountHint` to the inline script. The full file becomes:

```html
<!-- Card 1 front: Hanzi recognition.
     Hanzi rendered as ruby with pinyin hidden. No `[sound:...]` token appears
     anywhere in the front HTML — the {{soundfile:Audio}} filter (registered
     by the addon under note_type/Chinese_anki_decks/addon/) returns just the
     filename `foo.mp3`, so Anki's autoplay scanner has nothing to match. The
     Play Audio button feeds the filename to an HTML5 <audio> element on
     click. Backs still use {{Audio}} and autoplay normally. -->

<div class="card-side card-front">
  <div class="hanzi-block"
       id="hanzi-block"
       data-hanzi="{{text:Hanzi}}"
       data-pinyin="{{text:Pinyin}}"></div>
  <button class="toggle-btn" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

  <div class="audio-filename" id="audio-filename" hidden>{{soundfile:Audio}}</div>
  <button class="hint-btn" id="play-audio-btn" type="button">▶ Play Audio</button>

  {{#Hint}}
  <div class="hint-mount"
       data-hint="{{text:Hint}}"
       data-card-type="hanzi"></div>
  {{/Hint}}
</div>

<script src="_ruby.js"></script>
<script>
  (function () {
    window.ankiDecks.mountRuby("hanzi-block", { revealed: false });
    window.ankiDecks.attachToggle("hanzi-block", "toggle-pinyin-btn");

    var nameEl = document.getElementById("audio-filename");
    var filename = nameEl ? nameEl.textContent.trim() : "";
    window.ankiDecks.attachAudioButton("play-audio-btn", filename);

    window.ankiDecks.mountHint(".hint-mount");
  })();
</script>
```

- [ ] **Step 2: Update hanzi-recognition back**

Replace the entire contents of `note_type/Chinese_anki_decks/hanzi_recognition_back.html` with:

```html
<!-- Card 1 back: Hanzi recognition. Full reveal. Audio routed through HTML5
     (custom mount) so the addon's volume slider applies. Identical layout to
     the other two backs. -->

<div class="card-side card-back">
  <div class="hanzi-block show-all-ruby"
       id="hanzi-block"
       data-hanzi="{{text:Hanzi}}"
       data-pinyin="{{text:Pinyin}}"></div>
  <button class="toggle-btn" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

  <div class="audio-mount" data-soundfile="{{soundfile:Audio}}"></div>

  <hr>

  <div class="english">{{English}}</div>

  {{#Breakdown}}
  <div class="breakdown">{{Breakdown}}</div>
  {{/Breakdown}}

  {{#Examples}}
  <div class="examples-raw" hidden>{{Examples}}</div>
  <div class="examples"></div>
  {{/Examples}}

  {{#Context}}
  <div class="context-back">
    <span class="context-label">Context:</span>{{Context}}
  </div>
  {{/Context}}

  {{#Note}}
  <div class="note">{{Note}}</div>
  {{/Note}}

  {{#Hint}}
  <div class="hint-mount"
       data-hint="{{text:Hint}}"
       data-card-type="hanzi"
       data-revealed="true"></div>
  {{/Hint}}

  {{#PersonalNote}}
  <div class="personal-note">{{PersonalNote}}</div>
  {{/PersonalNote}}

  {{#Link}}
  <div class="link-footer"><a href="{{Link}}" target="_blank" rel="noopener">Read more →</a></div>
  {{/Link}}
</div>

<script src="_ruby.js"></script>
<script>
  (function () {
    window.ankiDecks.mountRuby("hanzi-block", { revealed: true });
    window.ankiDecks.attachToggle("hanzi-block", "toggle-pinyin-btn");
    window.ankiDecks.mountAutoplayAudio(".audio-mount");

    var raw = document.querySelector(".examples-raw");
    var target = document.querySelector(".examples");
    if (raw && target) {
      target.innerHTML = raw.innerHTML;
      raw.remove();
      window.ankiDecks.mountExamples(".examples");
    }

    window.ankiDecks.mountHint(".hint-mount");
  })();
</script>
```

- [ ] **Step 3: Commit**

```bash
git add note_type/Chinese_anki_decks/hanzi_recognition_front.html note_type/Chinese_anki_decks/hanzi_recognition_back.html
git commit -m "feat: hanzi-recognition card — Hint mount on both sides

Front: Hint button below the Play Audio button when Hint is non-empty
for this card type. Back: Hint auto-revealed labeled line + Context
labeled line, matching the production-card pattern with
data-card-type='hanzi'."
```

---

## Task 10: Audio-recognition card templates

**Files:**
- Modify: `note_type/Chinese_anki_decks/audio_recognition_front.html`
- Modify: `note_type/Chinese_anki_decks/audio_recognition_back.html`

- [ ] **Step 1: Replace audio-recognition front**

Replace the entire contents of `note_type/Chinese_anki_decks/audio_recognition_front.html` with:

```html
<!-- Card 2 front: Audio recognition.
     Audio autoplays via the custom HTML5 mount (volume controlled by the
     addon's toolbar slider). Hanzi hidden behind a hint button. On reveal,
     hanzi is mounted as ruby with pinyin still hidden so the user can
     hover/tap/toggle pinyin independently. -->

<div class="card-side card-front">
  <div class="audio-prominent audio-mount" data-soundfile="{{soundfile:Audio}}"></div>

  <button class="hint-btn" id="reveal-hanzi-btn" type="button">Show Hanzi</button>

  <div class="hanzi-block hidden"
       id="hanzi-block"
       data-hanzi="{{text:Hanzi}}"
       data-pinyin="{{text:Pinyin}}"></div>

  <button class="toggle-btn hidden" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

  {{#Hint}}
  <div class="hint-mount"
       data-hint="{{text:Hint}}"
       data-card-type="audio"></div>
  {{/Hint}}
</div>

<script src="_ruby.js"></script>
<script>
  (function () {
    window.ankiDecks.mountAutoplayAudio(".audio-mount");

    var revealBtn = document.getElementById("reveal-hanzi-btn");
    var hanziBlock = document.getElementById("hanzi-block");
    var toggleBtn = document.getElementById("toggle-pinyin-btn");
    revealBtn.addEventListener("click", function () {
      window.ankiDecks.mountRuby("hanzi-block", { revealed: false });
      hanziBlock.classList.remove("hidden");
      toggleBtn.classList.remove("hidden");
      revealBtn.classList.add("hidden");
      window.ankiDecks.attachToggle("hanzi-block", "toggle-pinyin-btn");
    });

    window.ankiDecks.mountHint(".hint-mount");
  })();
</script>
```

- [ ] **Step 2: Replace audio-recognition back**

Replace the entire contents of `note_type/Chinese_anki_decks/audio_recognition_back.html` with:

```html
<!-- Card 2 back: Audio recognition. Full reveal — replays audio via the
     custom mount, shows ruby fully expanded, then every field. Identical
     layout to the other two backs. -->

<div class="card-side card-back">
  <div class="hanzi-block show-all-ruby"
       id="hanzi-block"
       data-hanzi="{{text:Hanzi}}"
       data-pinyin="{{text:Pinyin}}"></div>
  <button class="toggle-btn" id="toggle-pinyin-btn" type="button">Toggle Pinyin</button>

  <div class="audio-mount" data-soundfile="{{soundfile:Audio}}"></div>

  <hr>

  <div class="english">{{English}}</div>

  {{#Breakdown}}
  <div class="breakdown">{{Breakdown}}</div>
  {{/Breakdown}}

  {{#Examples}}
  <div class="examples-raw" hidden>{{Examples}}</div>
  <div class="examples"></div>
  {{/Examples}}

  {{#Context}}
  <div class="context-back">
    <span class="context-label">Context:</span>{{Context}}
  </div>
  {{/Context}}

  {{#Note}}
  <div class="note">{{Note}}</div>
  {{/Note}}

  {{#Hint}}
  <div class="hint-mount"
       data-hint="{{text:Hint}}"
       data-card-type="audio"
       data-revealed="true"></div>
  {{/Hint}}

  {{#PersonalNote}}
  <div class="personal-note">{{PersonalNote}}</div>
  {{/PersonalNote}}

  {{#Link}}
  <div class="link-footer"><a href="{{Link}}" target="_blank" rel="noopener">Read more →</a></div>
  {{/Link}}
</div>

<script src="_ruby.js"></script>
<script>
  (function () {
    window.ankiDecks.mountRuby("hanzi-block", { revealed: true });
    window.ankiDecks.attachToggle("hanzi-block", "toggle-pinyin-btn");
    window.ankiDecks.mountAutoplayAudio(".audio-mount");

    var raw = document.querySelector(".examples-raw");
    var target = document.querySelector(".examples");
    if (raw && target) {
      target.innerHTML = raw.innerHTML;
      raw.remove();
      window.ankiDecks.mountExamples(".examples");
    }

    window.ankiDecks.mountHint(".hint-mount");
  })();
</script>
```

- [ ] **Step 3: Commit**

```bash
git add note_type/Chinese_anki_decks/audio_recognition_front.html note_type/Chinese_anki_decks/audio_recognition_back.html
git commit -m "feat: audio-recognition card — Hint mount on both sides

Same pattern as the other two cards, with data-card-type='audio'.
Front: Hint button below the show-hanzi reveal. Back: Hint
auto-revealed labeled line + Context labeled line."
```

---

## Task 11: INDEX renderer — surface Context

**Files:**
- Modify: `scripts/index.py` (the word-deck row renderer)

- [ ] **Step 1: Find the word-deck render function**

Open `scripts/index.py`. The word-deck row renderer is at line 175 onwards (note the function preceding line 189 where `note_html` is built — this is the word-deck path).

- [ ] **Step 2: Add context_html rendering**

In `scripts/index.py`, immediately before the `note_html` block (around line 189) add:

```python
    context_html = ""
    if row.context.strip():
        context_html = (
            f'<p class="context"><span class="context-label">Context:</span> '
            f'{html.escape(row.context)}</p>'
        )
```

Then in the f-string that builds the `<details>` body (around line 217-218), insert `{context_html}` right before `{note_html}`:

```python
        f'{breakdown_html}'
        f'{examples_html}'
        f'{context_html}'
        f'{note_html}'
        f'<div class="meta-row">{link_html}'
```

- [ ] **Step 3: Add CSS for the INDEX `.context` class**

Find the existing `.note { ... }` rule in `scripts/index.py` (around line 710). Add a sibling rule:

```python
.context { margin: 8px 0; font-size: 13px; color: #6b7280; }
.context-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
  margin-right: 6px;
}
```

If the existing CSS is inline in a Python triple-string, append to the same string.

- [ ] **Step 4: Run the renderer**

Run: `python scripts/index.py`

Expected: writes `INDEX.html` with no errors. No row has a Context value yet (all migrated rows have empty Context), so the new column produces no visible output yet. The validation here is that no exception is raised and the file regenerates cleanly.

- [ ] **Step 5: Verify Context renders by setting one row**

Pick a slang row to use as a test. Open `Chinese_Slang_Dialect_Flavor.tsv`, find the row for `杠杠的`, and set its Context column (7th col, between Note and Link) to `Northeastern slang`. Save.

Run: `python scripts/index.py` then open `INDEX.html` and search for `杠杠的`. Expected: a small "Context: Northeastern slang" line appears in the expanded entry.

Then `git restore Chinese_Slang_Dialect_Flavor.tsv` to remove the test edit (or keep it as a real Context for that row — the user can decide).

- [ ] **Step 6: Commit**

```bash
git add scripts/index.py
# Stage the slang TSV only if you decided to keep the test Context value as real data:
#   git add Chinese_Slang_Dialect_Flavor.tsv
git commit -m "feat: INDEX renderer — surface Context for word-deck rows

Renders a small 'Context: …' line inside each <details> body between
Examples and Note when the Context column is populated. Empty Context
collapses cleanly. Style mirrors the existing .note treatment."
```

---

## Task 12: Documentation updates

**Files:**
- Modify: `note_type/Chinese_anki_decks/README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update note-type README field list**

In `note_type/Chinese_anki_decks/README.md`, find the field-list block in step 1 of "One-time install" (around line 32):

```
   Hanzi
   Pinyin
   English
   Breakdown
   Examples
   Note
   Link
   PersonalNote
   Audio
```

Replace with:

```
   Hanzi
   Pinyin
   English
   Breakdown
   Examples
   Note
   Context
   Hint
   Link
   PersonalNote
   Audio
```

- [ ] **Step 2: Add a "Hint format" section to the README**

In `note_type/Chinese_anki_decks/README.md`, after the "How the templates work" section (around line 91 onwards), add a new section:

```markdown
### Context and Hint fields

`Context` is a terse disambiguator that always shows on the production
front above the English prompt and on all 3 backs above the Note line.
Use it when the English alone is ambiguous (e.g. for slang like 杠杠的
`awesome`, the Context `northeastern slang` rules out other ways to
say `awesome`). Keep it short — register / region / scenario tags work
best.

`Hint` is an optional click-to-reveal clue that appears on all 3
fronts (button) and auto-revealed on all 3 backs (labeled line). It
supports per-card-type formatting via line-leading prefixes:

| Hint field value | hanzi-recog front | audio-recog front | production front |
|---|---|---|---|
| `doubled syllable + 的` | same | same | same |
| `hanzi: starts with 杠<br>audio: doubled syllable<br>production: northeastern flavor` | `starts with 杠` | `doubled syllable` | `northeastern flavor` |
| `northeastern slang<br>audio: doubled syllable` | `northeastern slang` | `northeastern slang<br>doubled syllable` | `northeastern slang` |

Format rules:

- Split lines with literal `<br>` (the deck is `#html:true`).
- A line starting with `hanzi:`, `audio:`, or `production:`
  (case-insensitive, optional whitespace around the colon) scopes that
  line to the matching card type only.
- A line without a recognized prefix is universal — it shows on every
  card. Lines with an unrecognized prefix (e.g. `note:`) are also
  treated as universal; the validator warns when this happens because
  it's usually a typo.
```

- [ ] **Step 3: Update CLAUDE.md schema docs**

In `CLAUDE.md`, find the "File format" section's directive block (search for `#columns:Hanzi`):

```
#separator:tab
#html:true
#columns:Hanzi	Pinyin	English	Breakdown	Examples	Note	Link	Tags
#tags column:8
```

Replace with:

```
#separator:tab
#html:true
#columns:Hanzi	Pinyin	English	Breakdown	Examples	Note	Context	Hint	Link	Tags
#tags column:10
```

- [ ] **Step 4: Update CLAUDE.md column list**

In the same "File format" section, find the numbered list of columns. Update the count from 8 to 10. After the "Note" entry (item 6 in the old list), insert:

```
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
```

Renumber the remaining entries (Link → 9, Tags → 10).

- [ ] **Step 5: Commit**

```bash
git add note_type/Chinese_anki_decks/README.md CLAUDE.md
git commit -m "docs: schema 8 → 10 cols + Context/Hint usage

CLAUDE.md schema section documents the two new columns and their
purpose. Note-type README adds a 'Context and Hint fields' section
with the full per-card prefix format table."
```

---

## Task 13: End-to-end Anki verification

**Files:** None — manual verification.

- [ ] **Step 1: Final repo sanity check**

Run in sequence:

```bash
python scripts/validate.py
node note_type/Chinese_anki_decks/_ruby.test.js
python scripts/index.py
```

Expected:
- Validator: zero errors. Warnings only for pre-existing untagged/no-tier rows.
- JS tests: `parseHint: all tests passed`.
- Index renderer: writes `INDEX.html` cleanly, no exceptions.

- [ ] **Step 2: Update the Anki note type field list**

In Anki: `Tools → Manage Note Types → Chinese (anki-decks) → Fields…`. Add two new fields in this order:

1. Click `Add` → name `Context`. Use the Reposition button to place it after `Note` (between `Note` and `Link`).
2. Click `Add` → name `Hint`. Place after `Context` (between `Context` and `Link`).

Final field order in Anki should match the README:

```
Hanzi, Pinyin, English, Breakdown, Examples, Note, Context, Hint, Link, PersonalNote, Audio
```

- [ ] **Step 3: Update all 6 card templates in Anki**

`Tools → Manage Note Types → Chinese (anki-decks) → Cards…`. For each of the three cards (`1 Hanzi recognition`, `2 Audio recognition`, `3 Production`), paste the new contents of the corresponding `*_front.html` and `*_back.html` files from this repo.

Also paste the updated `styles.css` into the shared "Styling" pane.

Copy the updated `_ruby.js` into the Anki profile's `collection.media` folder (overwrite the existing file).

- [ ] **Step 4: Re-import all three TSVs**

`File → Import…` → each of the three word-deck TSVs in turn. Anki should report `Updated: N` for every row (matching on the Hanzi first field), `Added: 0`, `Skipped: 0`.

- [ ] **Step 5: Spot-check pre-existing rows**

In the Anki browser, open a few existing slang rows (e.g. 杠杠的, 哇塞, 牛逼) and verify Context + Hint fields are present but empty. Open any one card for each — front and back should render identically to before the change (no visual regressions when Context and Hint are empty).

- [ ] **Step 6: Add real test data — verify rendering**

Pick a slang row that currently has register info in `Note`. Example: 杠杠的, whose Note is `Northeastern-flavored slang.`. In Anki's browser, edit the note:

- Set `Context` to `northeastern slang`.
- Set `Hint` to `hanzi: doubled character<br>audio: doubled syllable + 的<br>production: northeastern flavor`.

Save. Then go to the deck and review the three cards for this note in turn:

- **Hanzi-recognition front**: shows the hanzi with pinyin hidden. A `Show hint` button appears below the Play Audio button. Click → reveals `Hint: doubled character`.
- **Hanzi-recognition back**: shows full reveal. The back has a labeled "Context: northeastern slang" line above Note, and a labeled "Hint: doubled character" line below Note. (Audio + production hint variants are filtered out because they don't apply to this card.)
- **Audio-recognition front**: plays audio. `Show hint` button → reveals `Hint: doubled syllable + 的`.
- **Audio-recognition back**: full reveal, Context line, Hint shows `doubled syllable + 的`.
- **Production front**: `northeastern slang` shows in small grey italic above `awesome / excellent`. `Show hint` button → reveals `Hint: northeastern flavor`.
- **Production back**: full reveal, Context line in body, Hint line shows `northeastern flavor`.

- [ ] **Step 7: Test the universal-hint case**

On a separate row, set `Hint` to `useful one-liner` (no prefix). Confirm all 3 fronts show the same "useful one-liner" when their reveal button is clicked, and all 3 backs auto-show it.

- [ ] **Step 8: Test the empty-after-filter case**

On a third row, set `Hint` to `production: prod only`. Confirm:

- Production front shows the button, reveals `prod only`.
- Hanzi and audio fronts do NOT show a button at all (parse result is empty for those card types).
- Hanzi and audio backs do NOT show a Hint line. Production back does.

- [ ] **Step 9: Test re-import idempotency**

Re-import all three TSVs once more. Anki should report `Updated: N`, `Added: 0`. Pick one of the rows you edited in Step 6 and verify the Context + Hint values are preserved (they're in Anki's note storage but not the TSV; the import only updates TSV-mapped fields, so they survive).

- [ ] **Step 10: Final commit (if any test data is to be kept in the TSV)**

If you decided in Step 6 to keep `northeastern slang` as a real Context value for `杠杠的` in the TSV (rather than only in Anki), add it to `Chinese_Slang_Dialect_Flavor.tsv` and commit:

```bash
git add Chinese_Slang_Dialect_Flavor.tsv
git commit -m "feat: seed Context on one slang row (杠杠的) as a usage demo"
```

Otherwise, no further commit is needed — the implementation is complete.

---

## Verification summary

After all tasks complete, the repo should have:

- 10-column TSVs (Core, Idioms, Slang), each row preserving all original data with two empty trailing fields inserted between Note and Link.
- `parseHint` + `mountHint` in `_ruby.js`, with Node tests passing.
- Updated card templates for all 3 cards × 2 sides (6 files).
- Updated styles.css with `.context-prompt`, `.context-back`, `.hint-mount`, `.hint-revealed`.
- Updated INDEX renderer surfacing Context.
- Updated README + CLAUDE.md.
- Validator passing clean against all three TSVs.
- One demonstrable Anki note (e.g. 杠杠的) showing all three card types rendering Context and a per-card-typed Hint correctly.
