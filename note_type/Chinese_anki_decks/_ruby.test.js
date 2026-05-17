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
