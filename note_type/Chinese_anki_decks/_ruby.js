/*
 * anki-decks ruby builder.
 *
 * Place this file inside Anki's `collection.media` folder. Card templates
 * include it via `<script src="_ruby.js">`. The leading underscore tells
 * Anki not to clean it up as unused media.
 *
 * Exposes `window.ankiDecks` with:
 *   mountRuby(containerId, { revealed })   - builds <ruby> from data-hanzi + data-pinyin
 *   attachToggle(containerId, buttonId)     - wires the toggle-pinyin button
 *   mountExamples(selector)                 - turns Examples field into <ul><li> ...
 */
(function () {
  "use strict";

  // Matches one CJK character. Mirrors HAN_RE in scripts/common.py.
  var HAN_RE = /[㐀-䶿一-鿿]/;

  function isHan(ch) {
    return HAN_RE.test(ch);
  }

  function buildRuby(hanzi, pinyinTokens) {
    var frag = document.createDocumentFragment();
    var tokenIdx = 0;
    var hanCount = 0;
    for (var i = 0; i < hanzi.length; i++) {
      hanCount += isHan(hanzi[i]) ? 1 : 0;
    }
    if (hanCount !== pinyinTokens.length) {
      // Misalignment — bail out to plain text and log.
      console.warn(
        "ruby: pinyin/hanzi count mismatch. hanzi=" + hanzi +
        " (" + hanCount + " han chars), pinyin tokens=" + pinyinTokens.length
      );
      frag.appendChild(document.createTextNode(hanzi));
      return frag;
    }
    for (var j = 0; j < hanzi.length; j++) {
      var ch = hanzi[j];
      if (isHan(ch)) {
        var ruby = document.createElement("ruby");
        ruby.appendChild(document.createTextNode(ch));
        var rt = document.createElement("rt");
        rt.appendChild(document.createTextNode(pinyinTokens[tokenIdx++]));
        ruby.appendChild(rt);
        ruby.addEventListener("click", function (e) {
          e.currentTarget.classList.toggle("revealed");
        });
        frag.appendChild(ruby);
      } else {
        frag.appendChild(document.createTextNode(ch));
      }
    }
    return frag;
  }

  function mountRuby(containerId, opts) {
    var el = document.getElementById(containerId);
    if (!el) return;
    var hanzi = el.getAttribute("data-hanzi") || "";
    var pinyin = el.getAttribute("data-pinyin") || "";
    var tokens = pinyin.split(/\s+/).filter(Boolean);
    el.textContent = "";
    el.appendChild(buildRuby(hanzi, tokens));
    if (opts && opts.revealed) {
      el.classList.add("show-all-ruby");
    } else {
      el.classList.remove("show-all-ruby");
    }
  }

  function attachToggle(containerId, buttonId) {
    var btn = document.getElementById(buttonId);
    var container = document.getElementById(containerId);
    if (!btn || !container) return;
    btn.addEventListener("click", function () {
      container.classList.toggle("show-all-ruby");
    });
  }

  function mountExamples(selector) {
    var nodes = document.querySelectorAll(selector);
    for (var i = 0; i < nodes.length; i++) {
      var raw = nodes[i].innerHTML;
      if (!raw) continue;
      var parts = raw.split(/<br\s*\/?>/i).map(function (p) {
        return p.trim();
      }).filter(Boolean);
      if (!parts.length) continue;
      var ul = document.createElement("ul");
      ul.className = "examples-list";
      for (var j = 0; j < parts.length; j++) {
        var seg = parts[j].split(/\s*\/\s*/);
        var li = document.createElement("li");
        var zh = document.createElement("span");
        zh.className = "example-zh";
        zh.textContent = seg[0] || "";
        li.appendChild(zh);
        if (seg.length > 1) {
          var en = document.createElement("span");
          en.className = "example-en";
          en.textContent = seg.slice(1).join(" / ");
          li.appendChild(en);
        }
        ul.appendChild(li);
      }
      nodes[i].textContent = "";
      nodes[i].appendChild(ul);
    }
  }

  window.ankiDecks = {
    mountRuby: mountRuby,
    attachToggle: attachToggle,
    mountExamples: mountExamples,
  };
})();
