#!/usr/bin/env python3
"""Generate INDEX.html — a self-contained browse view of all decks.

Reads every TSV at the repo root and writes a single HTML file with inlined
CSS + JS. The page renders ruby pinyin (hidden by default, reveal on hover /
per-row toggle / global toggle) and supports live filtering (search box, deck
checkboxes, tier checkboxes, tag chips). Per-row expansion via native
`<details>` surfaces Breakdown / Examples / Note / Link.

Source TSVs are not modified.

Usage:
  python scripts/index.py
"""

from __future__ import annotations

import html
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from common import (
    HAN_RE,
    REPO_ROOT,
    TIER_TAGS,
    deck_paths,
    parse_tsv,
    stderr,
)
from components_common import (
    COMPONENT_DECK_PATH,
    parse_component_tsv,
)

INDEX_PATH = REPO_ROOT / "INDEX.html"

DECK_TITLES = {
    "Chinese_Core_Conversation.tsv": "Core Conversation",
    "Chinese_Idioms_Proverbs_Classical.tsv": "Idioms / Proverbs / Classical",
    "Chinese_Slang_Dialect_Flavor.tsv": "Slang / Dialect / Flavor",
}
DECK_SLUGS = {
    "Chinese_Core_Conversation.tsv": "core",
    "Chinese_Idioms_Proverbs_Classical.tsv": "idioms",
    "Chinese_Slang_Dialect_Flavor.tsv": "slang",
}

COMPONENTS_SLUG = "components"
COMPONENTS_TITLE = "Phonetic Components"


def strip_diacritics(s: str) -> str:
    """NFD-decompose, drop combining marks. For diacritic-insensitive search."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)
    )


def build_ruby(hanzi: str, pinyin: str) -> str:
    """Render <ruby> markup. CJK chars get <ruby>+<rt>; other chars pass through.

    If the pinyin syllable count does not match the CJK char count, fall back
    to bare hanzi text — the validator should catch this at append time but the
    index stays viewable either way.
    """
    tokens = pinyin.split()
    han_count = len(HAN_RE.findall(hanzi))
    if han_count != len(tokens):
        return html.escape(hanzi)
    out: list[str] = []
    ti = 0
    for ch in hanzi:
        if HAN_RE.match(ch):
            out.append(
                f"<ruby>{html.escape(ch)}<rt>{html.escape(tokens[ti])}</rt></ruby>"
            )
            ti += 1
        else:
            out.append(html.escape(ch))
    return "".join(out)


def render_examples(raw: str) -> str:
    """Examples field is `中文。 / English.` chunks joined by literal <br>.

    Render as a <ul> with one <li> per chunk, splitting on the literal ' / '
    separator for the Chinese/English pair.
    """
    if not raw.strip():
        return ""
    chunks = [p.strip() for p in raw.split("<br>")]
    chunks = [c for c in chunks if c]
    if not chunks:
        return ""
    items: list[str] = []
    for chunk in chunks:
        if " / " in chunk:
            zh, en = chunk.split(" / ", 1)
        else:
            zh, en = chunk, ""
        item = f'<li><span class="zh">{html.escape(zh)}</span>'
        if en:
            item += f'<span class="en">{html.escape(en)}</span>'
        item += "</li>"
        items.append(item)
    return f'<ul class="examples">{"".join(items)}</ul>'


def render_breakdown(raw: str) -> str:
    """Breakdown is space-separated `char (gloss) char (gloss) ...` groups.

    Render each group in its own <span> so they wrap gracefully and look
    grouped. If parsing fails for any reason, fall back to the raw string.
    """
    raw = raw.strip()
    if not raw:
        return ""
    # Walk char-by-char to split on space-between-groups but preserve internal
    # parens. A group is: `<one or more non-( chars> (<gloss>)`.
    parts: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i].isspace():
            i += 1
            continue
        start = i
        # Consume up to '('
        while i < len(raw) and raw[i] != "(":
            i += 1
        if i >= len(raw):
            parts.append(raw[start:].strip())
            break
        # Consume the '(...)' group
        depth = 0
        while i < len(raw):
            if raw[i] == "(":
                depth += 1
            elif raw[i] == ")":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        parts.append(raw[start:i].strip())
    spans = "".join(f'<span class="bd-item">{html.escape(p)}</span>' for p in parts if p)
    return f'<p class="breakdown">{spans}</p>'


def render_entry(row, deck_slug: str) -> str:
    tier = ""
    topical: list[str] = []
    for t in row.tags:
        if t in TIER_TAGS:
            tier = t
        else:
            topical.append(t)
    all_tags = " ".join(row.tags)

    search_blob = " ".join(
        [
            row.hanzi,
            row.pinyin,
            strip_diacritics(row.pinyin),
            row.english.lower(),
        ]
    )
    search_blob = strip_diacritics(search_blob).lower()

    ruby_html = build_ruby(row.hanzi, row.pinyin)
    breakdown_html = render_breakdown(row.breakdown)
    examples_html = render_examples(row.examples)

    note_html = ""
    if row.note.strip():
        note_html = f'<p class="note">{html.escape(row.note)}</p>'

    link_html = ""
    if row.link.strip():
        link_html = (
            f'<a class="link" href="{html.escape(row.link, quote=True)}" '
            f'target="_blank" rel="noopener">Read more →</a>'
        )

    tag_chips = "".join(
        f'<button class="tag-chip" type="button" data-tag="{html.escape(t, quote=True)}">'
        f"{html.escape(t)}</button>"
        for t in row.tags
    )

    return (
        f'<details class="entry" data-deck="{html.escape(deck_slug, quote=True)}" '
        f'data-tier="{html.escape(tier, quote=True)}" '
        f'data-tags="{html.escape(all_tags, quote=True)}" '
        f'data-search="{html.escape(search_blob, quote=True)}">'
        f"<summary>"
        f'<span class="hanzi-block" data-hanzi="{html.escape(row.hanzi, quote=True)}" '
        f'data-pinyin="{html.escape(row.pinyin, quote=True)}">{ruby_html}</span>'
        f'<span class="english">{html.escape(row.english)}</span>'
        f'</summary>'
        f'<div class="details-body">'
        f'{breakdown_html}'
        f'{examples_html}'
        f'{note_html}'
        f'<div class="meta-row">{link_html}'
        f'<div class="tag-chips">{tag_chips}</div></div>'
        f'</div></details>'
    )


def render_component_entry(row) -> str:
    """Render a single phonetic-component row. Different schema from word rows
    so renders into its own DOM shape, but uses the same `details.entry`
    wrapper so filtering / search / deck-filter integrate cleanly."""
    search_blob = " ".join([
        row.component,
        row.pinyin,
        strip_diacritics(row.pinyin),
        row.meaning.lower(),
        row.member_chars,
    ])
    search_blob = strip_diacritics(search_blob).lower()

    member_html = ""
    if row.member_chars:
        member_html = (
            f'<div class="component-members">'
            f'<span class="component-members-label">members:</span> '
            f'<span class="component-members-chars">{html.escape(row.member_chars)}</span>'
            f'</div>'
        )

    stat_parts: list[str] = []
    if row.reliability:
        stat_parts.append(f"reliability {html.escape(row.reliability)}")
    if row.productivity:
        stat_parts.append(f"in {html.escape(row.productivity)} chars")
    if row.frequency:
        stat_parts.append(f"freq #{html.escape(row.frequency)}")
    stats_html = ""
    if stat_parts:
        stats_html = f'<div class="component-reliability">{" · ".join(stat_parts)}</div>'

    note_html = ""
    if row.note.strip():
        note_html = f'<p class="note">{row.note}</p>'

    link_html = ""
    if row.link.strip():
        link_html = (
            f'<a class="link" href="{html.escape(row.link, quote=True)}" '
            f'target="_blank" rel="noopener">HanziCraft →</a>'
        )

    tag_chips = "".join(
        f'<button class="tag-chip" type="button" data-tag="{html.escape(t, quote=True)}">'
        f"{html.escape(t)}</button>"
        for t in row.tags
    )

    pinyin_html = ""
    if row.pinyin:
        pinyin_html = (
            f'<span class="component-pinyin">{html.escape(row.pinyin)}</span>'
        )

    return (
        f'<details class="entry component-entry" '
        f'data-deck="{html.escape(COMPONENTS_SLUG, quote=True)}" '
        f'data-tier="" '
        f'data-tags="{html.escape(" ".join(row.tags), quote=True)}" '
        f'data-search="{html.escape(search_blob, quote=True)}">'
        f'<summary>'
        f'<span class="component-headline">{html.escape(row.component)}</span>'
        f'{pinyin_html}'
        f'<span class="english">{html.escape(row.meaning)}</span>'
        f'</summary>'
        f'<div class="details-body">'
        f'{member_html}'
        f'{stats_html}'
        f'{note_html}'
        f'<div class="meta-row">{link_html}<div class="tag-chips">{tag_chips}</div></div>'
        f'</div></details>'
    )


STYLE = """
:root {
  --bg: #fafafa;
  --bg-elev: #fff;
  --fg: #1a1a1a;
  --fg-muted: #4b5563;
  --fg-faint: #6b7280;
  --border: #e5e7eb;
  --accent: #6366f1;
  --accent-soft: #eef2ff;
  --ruby: #6b46c1;
  --personal: #fef3c7;
  --personal-border: #f59e0b;
  --tag-bg: #f3f4f6;
  --tag-active-bg: #6366f1;
  --tag-active-fg: #fff;
  --header-bg: rgba(250, 250, 250, 0.92);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16161a;
    --bg-elev: #1f1f23;
    --fg: #e8e8e8;
    --fg-muted: #b8b8b8;
    --fg-faint: #9ca3af;
    --border: #2c2c30;
    --accent: #a5b4fc;
    --accent-soft: #2a2a40;
    --ruby: #c4b5fd;
    --personal: rgba(245, 158, 11, 0.12);
    --personal-border: #d97706;
    --tag-bg: #2a2a2e;
    --tag-active-bg: #a5b4fc;
    --tag-active-fg: #16161a;
    --header-bg: rgba(22, 22, 26, 0.92);
  }
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
  font-size: 15px;
}
main { max-width: 1100px; margin: 0 auto; padding: 16px; }

header.page-header {
  position: sticky; top: 0; z-index: 10;
  background: var(--header-bg);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  padding: 14px 18px;
}
header.page-header h1 { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
header.page-header .totals { color: var(--fg-faint); font-size: 13px; margin-bottom: 12px; }

.controls { display: grid; gap: 10px; grid-template-columns: 1fr; }
@media (min-width: 720px) {
  .controls { grid-template-columns: 1fr auto auto; align-items: end; }
}
.controls input[type="search"] {
  width: 100%;
  font-family: inherit;
  font-size: 14px;
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-elev);
  color: var(--fg);
}
.controls input[type="search"]:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.controls fieldset {
  border: none; padding: 0; margin: 0;
  display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
}
.controls fieldset legend { font-size: 11px; color: var(--fg-faint); padding: 0 6px 0 0; text-transform: uppercase; letter-spacing: 0.05em; }
.controls label { font-size: 13px; display: inline-flex; gap: 5px; align-items: center; user-select: none; cursor: pointer; }
.controls label input { margin: 0; }
.controls-bottom { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.controls-bottom .label { font-size: 11px; color: var(--fg-faint); text-transform: uppercase; letter-spacing: 0.05em; margin-right: 4px; }
.actions { display: flex; gap: 8px; margin-left: auto; }
.actions button {
  font: inherit; font-size: 12px;
  padding: 5px 11px;
  background: var(--bg-elev); color: var(--fg);
  border: 1px solid var(--border); border-radius: 999px;
  cursor: pointer;
}
.actions button:hover { background: var(--tag-bg); }

.tag-chip {
  font: inherit; font-size: 12px;
  padding: 3px 9px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--tag-bg);
  color: var(--fg-muted);
  cursor: pointer;
  white-space: nowrap;
}
.tag-chip:hover { color: var(--fg); }
.tag-chip.active {
  background: var(--tag-active-bg);
  color: var(--tag-active-fg);
  border-color: var(--tag-active-bg);
}

section.deck { margin: 24px 0; }
section.deck > h2 {
  font-size: 17px;
  font-weight: 600;
  margin: 0 0 4px;
  padding-bottom: 6px;
  border-bottom: 2px solid var(--border);
}
section.tag-group { margin: 14px 0; }
section.tag-group > h3 {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--fg-faint);
  margin: 12px 0 6px;
}
.count {
  font-weight: 400;
  color: var(--fg-faint);
  margin-left: 6px;
  font-size: 0.85em;
}

details.entry {
  background: var(--bg-elev);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  margin: 6px 0;
}
details.entry[open] { box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
details.entry > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 4px 0;
}
details.entry > summary::-webkit-details-marker { display: none; }
details.entry > summary::before {
  content: "▸";
  color: var(--fg-faint);
  font-size: 11px;
  transition: transform 120ms ease;
}
details.entry[open] > summary::before { transform: rotate(90deg); }

.hanzi-block {
  font-family: "Kaiti SC", "STKaiti", "KaiTi", "楷体",
    "Noto Serif CJK SC", "Source Han Serif SC",
    "Songti SC", "SimSun", "宋体", serif;
  font-size: 26px;
  line-height: 1.7;
}
.hanzi-block ruby { cursor: pointer; -webkit-user-select: none; user-select: none; }
.hanzi-block ruby rt {
  font-family: "Helvetica Neue", "Segoe UI", system-ui, sans-serif;
  font-size: 0.42em;
  color: var(--ruby);
  opacity: 0;
  transition: opacity 120ms ease;
  user-select: none;
}
.hanzi-block ruby:hover rt,
.hanzi-block ruby.revealed rt,
.hanzi-block.show-all-ruby ruby rt { opacity: 1; }

.english { color: var(--fg-muted); font-size: 14px; flex: 1; }

.details-body {
  padding: 10px 4px 4px;
  margin-top: 4px;
  border-top: 1px solid var(--border);
  color: var(--fg-muted);
}
.breakdown { margin: 8px 0; line-height: 2; font-size: 13px; }
.bd-item {
  display: inline-block;
  background: var(--tag-bg);
  padding: 1px 7px;
  border-radius: 4px;
  margin-right: 4px;
  margin-bottom: 4px;
  font-size: 13px;
  color: var(--fg);
}
.examples { list-style: none; padding: 0; margin: 8px 0; }
.examples li {
  margin: 6px 0;
  padding: 6px 10px;
  border-left: 3px solid var(--border);
  background: var(--bg);
  border-radius: 0 4px 4px 0;
}
.examples .zh {
  display: block;
  font-family: "Kaiti SC", "STKaiti", "KaiTi", serif;
  font-size: 16px;
  color: var(--fg);
}
.examples .en {
  display: block;
  font-size: 13px;
  font-style: italic;
  color: var(--fg-faint);
  margin-top: 2px;
}
.note { margin: 8px 0; font-size: 13px; }
.meta-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 10px; }
.link {
  color: var(--accent);
  font-size: 13px;
  text-decoration: none;
  border-bottom: 1px solid currentColor;
}
.link:hover { opacity: 0.7; }
.tag-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-left: auto; }

[hidden] { display: none !important; }

section.deck:not(:has(details.entry:not([hidden]))) { display: none; }
section.tag-group:not(:has(details.entry:not([hidden]))) { display: none; }

.empty-state {
  text-align: center;
  color: var(--fg-faint);
  padding: 60px 0;
  font-size: 14px;
  display: none;
}
.empty-state.visible { display: block; }

/* ---------- Phonetic-components section ---------- */

details.component-entry > summary {
  gap: 12px;
}
.component-headline {
  font-family: "Kaiti SC", "STKaiti", "KaiTi", "楷体",
    "Noto Serif CJK SC", "Source Han Serif SC",
    "Songti SC", "SimSun", "宋体", serif;
  font-size: 30px;
  line-height: 1;
  min-width: 1.4em;
  text-align: center;
}
.component-pinyin {
  font-family: "Helvetica Neue", "Segoe UI", system-ui, sans-serif;
  font-size: 16px;
  font-weight: 500;
  color: var(--ruby);
  min-width: 4em;
}
.component-members {
  margin: 6px 0;
  font-size: 13px;
}
.component-members-label {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 11px;
  color: var(--fg-faint);
}
.component-members-chars {
  font-family: "Kaiti SC", "STKaiti", "KaiTi", "楷体", serif;
  font-size: 20px;
  letter-spacing: 0.04em;
  color: var(--fg);
}
.component-reliability {
  font-size: 12px;
  color: var(--fg-faint);
  margin: 6px 0;
  font-variant-numeric: tabular-nums;
}
"""


SCRIPT = r"""
(function () {
  "use strict";

  const $search = document.getElementById("search");
  const $reset = document.getElementById("reset");
  const $togglePinyin = document.getElementById("toggle-pinyin");
  const $deckBoxes = Array.from(document.querySelectorAll(".deck-filter"));
  const $tierBoxes = Array.from(document.querySelectorAll(".tier-filter"));
  const $tagChips = Array.from(document.querySelectorAll("#tag-filter .tag-chip"));
  const $entries = Array.from(document.querySelectorAll("details.entry"));
  const $emptyState = document.getElementById("empty-state");
  const $visibleCount = document.getElementById("visible-count");

  function stripDiacritics(s) {
    return s.normalize("NFD").replace(/\p{Diacritic}/gu, "");
  }
  function normalize(s) {
    return stripDiacritics(s).toLowerCase();
  }

  const activeTags = new Set();

  function activeDecks() {
    return new Set($deckBoxes.filter(b => b.checked).map(b => b.value));
  }
  function activeTiers() {
    return new Set($tierBoxes.filter(b => b.checked).map(b => b.value));
  }

  function applyFilters() {
    const q = normalize($search.value.trim());
    const decks = activeDecks();
    const tiers = activeTiers();
    const tagSel = activeTags;
    let visible = 0;
    for (const el of $entries) {
      const deck = el.dataset.deck;
      const tier = el.dataset.tier;
      const tagsList = el.dataset.tags ? el.dataset.tags.split(/\s+/) : [];
      const search = el.dataset.search || "";

      let pass = true;
      if (!decks.has(deck)) pass = false;
      if (pass && tier && !tiers.has(tier)) pass = false;
      if (pass && tagSel.size > 0) {
        let any = false;
        for (const t of tagsList) {
          if (tagSel.has(t)) { any = true; break; }
        }
        if (!any) pass = false;
      }
      if (pass && q && !search.includes(q)) pass = false;

      el.hidden = !pass;
      if (pass) visible++;
    }
    $visibleCount.textContent = visible;
    $emptyState.classList.toggle("visible", visible === 0);
  }

  function setTagActive(tag, active) {
    if (active) activeTags.add(tag);
    else activeTags.delete(tag);
    for (const chip of $tagChips) {
      if (chip.dataset.tag === tag) chip.classList.toggle("active", active);
    }
  }

  // Header tag chips toggle their tag.
  for (const chip of $tagChips) {
    chip.addEventListener("click", () => {
      const tag = chip.dataset.tag;
      setTagActive(tag, !activeTags.has(tag));
      applyFilters();
    });
  }

  // Tag chips inside entry details add that tag to the active set.
  document.addEventListener("click", (e) => {
    const chip = e.target.closest(".details-body .tag-chip");
    if (!chip) return;
    e.preventDefault();
    const tag = chip.dataset.tag;
    setTagActive(tag, true);
    applyFilters();
    document.querySelector("header.page-header").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  $search.addEventListener("input", applyFilters);
  for (const b of [...$deckBoxes, ...$tierBoxes]) {
    b.addEventListener("change", applyFilters);
  }

  $reset.addEventListener("click", () => {
    $search.value = "";
    for (const b of $deckBoxes) b.checked = true;
    for (const b of $tierBoxes) b.checked = true;
    activeTags.clear();
    for (const chip of $tagChips) chip.classList.remove("active");
    applyFilters();
  });

  // Global pinyin toggle.
  let allShown = false;
  $togglePinyin.addEventListener("click", () => {
    allShown = !allShown;
    for (const block of document.querySelectorAll(".hanzi-block")) {
      block.classList.toggle("show-all-ruby", allShown);
    }
    $togglePinyin.textContent = allShown ? "Hide all pinyin" : "Show all pinyin";
  });

  // Per-character tap-to-reveal (mobile) — same pattern as the Anki card.
  // stopPropagation so clicking a single character doesn't also toggle the
  // surrounding <details> via the summary bubble.
  document.addEventListener("click", (e) => {
    const ruby = e.target.closest(".hanzi-block ruby");
    if (!ruby) return;
    ruby.classList.toggle("revealed");
    e.stopPropagation();
    e.preventDefault();
  });

  applyFilters();
})();
"""


def main() -> int:
    paths = deck_paths()
    if not paths:
        stderr("no TSV files found")
        return 1

    decks: list[tuple[Path, list]] = []
    total = 0
    all_tags: set[str] = set()
    deck_counts: dict[str, int] = {}

    for path in paths:
        try:
            _, rows = parse_tsv(path)
        except ValueError as e:
            stderr(f"skipping {path.name}: {e}")
            continue
        decks.append((path, rows))
        total += len(rows)
        deck_counts[DECK_SLUGS.get(path.name, path.stem)] = len(rows)
        for r in rows:
            for t in r.tags:
                if t not in TIER_TAGS:
                    all_tags.add(t)

    # Phonetic-components deck has a different schema and isn't returned by
    # deck_paths(). Load it separately if present.
    component_rows: list = []
    if COMPONENT_DECK_PATH.exists():
        try:
            _, component_rows = parse_component_tsv(COMPONENT_DECK_PATH)
        except ValueError as e:
            stderr(f"skipping {COMPONENT_DECK_PATH.name}: {e}")
            component_rows = []
        else:
            total += len(component_rows)
            deck_counts[COMPONENTS_SLUG] = len(component_rows)
            for r in component_rows:
                for t in r.tags:
                    if t not in TIER_TAGS:
                        all_tags.add(t)

    # ---- Build header controls ----

    deck_boxes = "".join(
        f'<label><input type="checkbox" class="deck-filter" value="{slug}" checked> '
        f"{html.escape(DECK_TITLES[name])} <span class=\"count\">{deck_counts[slug]}</span></label>"
        for name, slug in DECK_SLUGS.items()
        if slug in deck_counts
    )
    if COMPONENTS_SLUG in deck_counts:
        deck_boxes += (
            f'<label><input type="checkbox" class="deck-filter" '
            f'value="{COMPONENTS_SLUG}" checked> '
            f'{html.escape(COMPONENTS_TITLE)} '
            f'<span class="count">{deck_counts[COMPONENTS_SLUG]}</span></label>'
        )

    tier_boxes = "".join(
        f'<label><input type="checkbox" class="tier-filter" value="{html.escape(t)}" checked> '
        f"{html.escape(t)}</label>"
        for t in sorted(TIER_TAGS)
    )

    tag_chips = "".join(
        f'<button class="tag-chip" type="button" data-tag="{html.escape(t, quote=True)}">'
        f"{html.escape(t)}</button>"
        for t in sorted(all_tags)
    )

    parts = [f"{total} entries"]
    parts += [
        f"{DECK_TITLES[name].split(' ', 1)[0]} {deck_counts[slug]}"
        for name, slug in DECK_SLUGS.items() if slug in deck_counts
    ]
    if COMPONENTS_SLUG in deck_counts:
        parts.append(f"Components {deck_counts[COMPONENTS_SLUG]}")
    totals_text = " · ".join(parts)

    # ---- Build body sections ----

    body_sections: list[str] = []
    for path, rows in decks:
        slug = DECK_SLUGS.get(path.name, path.stem)
        title = DECK_TITLES.get(path.name, path.stem)

        by_tag: dict[str, list] = defaultdict(list)
        untagged: list = []
        for r in rows:
            topical = [t for t in r.tags if t not in TIER_TAGS]
            if not topical:
                if not r.tags:
                    untagged.append(r)
                else:
                    # Tier-only tagged — bucket under a synthetic group so the
                    # tier filter still applies but the tag header is clear.
                    by_tag["(no topical tag)"].append(r)
            else:
                for t in topical:
                    by_tag[t].append(r)

        tag_groups_html: list[str] = []
        for tag in sorted(by_tag):
            entries_html = "".join(
                render_entry(r, slug) for r in sorted(by_tag[tag], key=lambda r: r.line_no)
            )
            tag_groups_html.append(
                f'<section class="tag-group" data-tag="{html.escape(tag, quote=True)}">'
                f"<h3>{html.escape(tag)} <span class=\"count\">{len(by_tag[tag])}</span></h3>"
                f"{entries_html}</section>"
            )
        if untagged:
            entries_html = "".join(
                render_entry(r, slug) for r in sorted(untagged, key=lambda r: r.line_no)
            )
            tag_groups_html.append(
                f'<section class="tag-group" data-tag="">'
                f"<h3><em>untagged</em> <span class=\"count\">{len(untagged)}</span></h3>"
                f"{entries_html}</section>"
            )

        body_sections.append(
            f'<section class="deck" data-deck="{html.escape(slug, quote=True)}">'
            f"<h2>{html.escape(title)} <span class=\"count\">{len(rows)}</span></h2>"
            f"{''.join(tag_groups_html)}</section>"
        )

    # Phonetic-components section (separate schema, simpler layout — flat list,
    # no tag-group buckets since the deck currently uses a single tag).
    if component_rows:
        comp_entries = "".join(
            render_component_entry(r)
            for r in sorted(component_rows, key=lambda r: r.line_no)
        )
        body_sections.append(
            f'<section class="deck" data-deck="{html.escape(COMPONENTS_SLUG, quote=True)}">'
            f"<h2>{html.escape(COMPONENTS_TITLE)} "
            f"<span class=\"count\">{len(component_rows)}</span></h2>"
            f"{comp_entries}</section>"
        )

    # ---- Assemble page ----

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Anki Deck Index — {total} entries</title>
<style>{STYLE}</style>
</head>
<body>
<header class="page-header">
  <h1>Anki Deck Index</h1>
  <div class="totals" id="totals">
    <span id="visible-count">{total}</span> of {total} visible · {html.escape(totals_text)}
  </div>
  <div class="controls">
    <input type="search" id="search" placeholder="Search hanzi / pinyin / english (diacritic-insensitive)…" autocomplete="off" spellcheck="false">
    <fieldset><legend>Deck</legend>{deck_boxes}</fieldset>
    <fieldset><legend>Tier</legend>{tier_boxes}</fieldset>
  </div>
  <div class="controls-bottom" id="tag-filter">
    <span class="label">Tags</span>{tag_chips}
    <div class="actions">
      <button type="button" id="toggle-pinyin">Show all pinyin</button>
      <button type="button" id="reset">Reset filters</button>
    </div>
  </div>
</header>
<main>
{''.join(body_sections)}
<div class="empty-state" id="empty-state">No entries match the current filters.</div>
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""

    INDEX_PATH.write_text(page, encoding="utf-8")
    print(f"wrote {INDEX_PATH.relative_to(REPO_ROOT)} ({total} entries).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
