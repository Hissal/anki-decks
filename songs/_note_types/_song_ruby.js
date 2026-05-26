/*
 * Song-deck ruby helpers. Drop this file in Anki's collection.media/
 * alongside the existing _ruby.js (from the word decks). The leading
 * underscore keeps Anki from purging it as unused media.
 *
 * Two mount modes:
 *
 *   mountElement(elementId)
 *     Reads textContent + data-pinyin from a single-line element and
 *     rebuilds the DOM with <ruby> markup, PRESERVING any wrapping
 *     elements such as Anki's <span class="cloze"> around the revealed
 *     answer. This is what keeps the red-accented cloze styling on the
 *     back side of cloze cards.
 *
 *   mountLines(containerId)
 *     For SongBlock cards: the container's innerHTML is N lines joined by
 *     <br>, possibly with one line wrapped as <span class="cloze">…</span>.
 *     Splits on <br>, parses data-pinyin (also <br>-separated), and
 *     replaces each non-blanked line with a <span class="lines-line">
 *     holding a ruby build. Cloze-blanked lines ("[...]") pass through
 *     unchanged so the gap stays visible.
 */
(function () {
  "use strict";

  var HAN_RE = /[㐀-䶿一-鿿]/;
  function isHan(ch) { return HAN_RE.test(ch); }

  /** Count CJK characters across a node and all descendants. */
  function countHan(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      var c = 0;
      for (var i = 0; i < node.nodeValue.length; i++) {
        if (isHan(node.nodeValue[i])) c++;
      }
      return c;
    }
    if (node.nodeType === Node.ELEMENT_NODE) {
      var total = 0;
      for (var j = 0; j < node.childNodes.length; j++) {
        total += countHan(node.childNodes[j]);
      }
      return total;
    }
    return 0;
  }

  /** Build a single <ruby> for one CJK char + pinyin token. */
  function makeRuby(ch, pinyinToken) {
    var ruby = document.createElement("ruby");
    ruby.appendChild(document.createTextNode(ch));
    var rt = document.createElement("rt");
    rt.appendChild(document.createTextNode(pinyinToken));
    ruby.appendChild(rt);
    ruby.addEventListener("click", function (e) {
      e.currentTarget.classList.toggle("revealed");
    });
    return ruby;
  }

  /**
   * Walk a node's children. For text nodes, emit one <ruby> per CJK char
   * (consuming one token from `state` per char). For element nodes, clone
   * the element shallowly and recurse into its children, preserving any
   * wrapper class (notably Anki's <span class="cloze">…</span>).
   *
   * Returns a DocumentFragment that is the rebuilt version of `parent`'s
   * children — caller is expected to replace `parent`'s contents with it.
   */
  function processChildren(parent, state) {
    var frag = document.createDocumentFragment();
    for (var i = 0; i < parent.childNodes.length; i++) {
      var child = parent.childNodes[i];
      if (child.nodeType === Node.TEXT_NODE) {
        var text = child.nodeValue;
        for (var j = 0; j < text.length; j++) {
          var ch = text[j];
          if (isHan(ch)) {
            frag.appendChild(makeRuby(ch, state.tokens[state.idx++]));
          } else {
            frag.appendChild(document.createTextNode(ch));
          }
        }
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        var clone = child.cloneNode(false);
        var inner = processChildren(child, state);
        clone.appendChild(inner);
        frag.appendChild(clone);
      }
    }
    return frag;
  }

  function rebuildWithRuby(el, pinyin) {
    var tokens = String(pinyin).split(/\s+/).filter(Boolean);
    var hanCount = countHan(el);
    if (hanCount !== tokens.length) {
      // Mismatch — leave the element alone so we don't corrupt the display.
      // (Common case: front-side cloze render where one word is "[...]" so
      // the hanzi count is short of the full-line pinyin.)
      return;
    }
    var state = { tokens: tokens, idx: 0 };
    var rebuilt = processChildren(el, state);
    el.innerHTML = "";
    el.appendChild(rebuilt);
  }

  function mountElement(elementId) {
    var el = document.getElementById(elementId);
    if (!el) return;
    var pinyin = el.getAttribute("data-pinyin") || "";
    rebuildWithRuby(el, pinyin);
  }

  /** Heuristic: a line is "blanked" if its trimmed text content looks like
   *  "[...]" (Anki's default cloze placeholder, with or without dots). */
  function looksBlanked(nodeText) {
    var t = (nodeText || "").trim();
    return /^\[[^\]]*\]$/.test(t);
  }

  function mountLines(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return;
    var html = el.innerHTML;
    var pinyinField = el.getAttribute("data-pinyin") || "";
    // Split the container's HTML on <br>, mirroring the data-pinyin split.
    var hanziHtmlLines = html.split(/<br\s*\/?>/i);
    var pinyinLines = pinyinField.split(/<br\s*\/?>/i).map(function (s) { return s.trim(); });
    el.innerHTML = "";
    for (var i = 0; i < hanziHtmlLines.length; i++) {
      var rawHtml = hanziHtmlLines[i];
      var pyLine = pinyinLines[i] || "";
      if (!rawHtml.trim() && !pyLine) continue;
      var lineWrap = document.createElement("span");
      lineWrap.className = "lines-line";
      // Parse the line's HTML into a temp container so we can DOM-walk it.
      var temp = document.createElement("div");
      temp.innerHTML = rawHtml;
      if (looksBlanked(temp.textContent)) {
        // Cloze blank — leave HTML intact (preserves Anki's .cloze span).
        lineWrap.innerHTML = rawHtml;
      } else {
        rebuildWithRuby(temp, pyLine);
        // Move rebuilt children into the line wrapper.
        while (temp.firstChild) lineWrap.appendChild(temp.firstChild);
      }
      el.appendChild(lineWrap);
    }
  }

  window.songsRuby = {
    mountElement: mountElement,
    mountLines: mountLines,
  };
})();
