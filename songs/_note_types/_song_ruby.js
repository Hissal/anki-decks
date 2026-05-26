/*
 * Song-deck ruby helpers. Drop this file in Anki's collection.media/
 * alongside the existing _ruby.js (from the word decks). The leading
 * underscore keeps Anki from purging it as unused media.
 *
 * Builds on `_ruby.js`'s lower-level helpers, adding two song-specific
 * mount modes:
 *
 *   mountElement(elementId)
 *     Reads textContent + data-pinyin from a single-line element and
 *     replaces its contents with a <ruby> tree (hover/tap reveals rt).
 *     Use this when Anki has already rendered cloze deletions so the
 *     element's text matches the original Hanzi line.
 *
 *   mountLines(containerId)
 *     For SongBlock cards: the container's innerHTML is N lines joined by
 *     <br>, with one line possibly wrapped as <span class="cloze">[…]</span>.
 *     Splits on <br>, parses data-pinyin (also <br>-separated, one line per
 *     row), and replaces each non-cloze line with a <ruby> markup.
 *     Cloze-blanked lines pass through unchanged so the "[…]" gap stays
 *     visible.
 */
(function () {
  "use strict";

  var HAN_RE = /[㐀-䶿一-鿿]/;
  function isHan(ch) { return HAN_RE.test(ch); }

  function buildRubyFragment(hanzi, pinyinTokens) {
    var frag = document.createDocumentFragment();
    var hanCount = 0;
    for (var i = 0; i < hanzi.length; i++) hanCount += isHan(hanzi[i]) ? 1 : 0;
    if (hanCount !== pinyinTokens.length) {
      // Counts don't match — bail with plain text so we don't corrupt
      // the display. (Common case: pinyin field has extra syllables for
      // a cloze that was blanked in the displayed text.)
      frag.appendChild(document.createTextNode(hanzi));
      return frag;
    }
    var idx = 0;
    for (var j = 0; j < hanzi.length; j++) {
      var ch = hanzi[j];
      if (isHan(ch)) {
        var ruby = document.createElement("ruby");
        ruby.appendChild(document.createTextNode(ch));
        var rt = document.createElement("rt");
        rt.appendChild(document.createTextNode(pinyinTokens[idx++]));
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

  function mountElement(elementId) {
    var el = document.getElementById(elementId);
    if (!el) return;
    var hanzi = el.textContent;
    var pinyin = el.getAttribute("data-pinyin") || "";
    var tokens = pinyin.split(/\s+/).filter(Boolean);
    el.textContent = "";
    el.appendChild(buildRubyFragment(hanzi, tokens));
  }

  /** Split an HTML string on <br>, returning an array of pieces. */
  function splitOnBr(html) {
    return html.split(/<br\s*\/?>/i);
  }

  /** Strip HTML tags but keep textContent — for matching against pinyin tokens. */
  function stripTags(html) {
    var div = document.createElement("div");
    div.innerHTML = html;
    return div.textContent;
  }

  /** Build a single line: either a plain ruby render, or pass-through HTML for
   * lines whose text looks like a cloze blank ("[...]" or empty). */
  function buildLineNode(rawHtml, pinyinLine) {
    var line = document.createElement("span");
    line.className = "lines-line";
    var text = stripTags(rawHtml).trim();
    // A cloze-blanked line on the front side renders as "[...]". Show the
    // raw HTML (which includes the .cloze span Anki added) so the styling
    // still applies, but skip the ruby build.
    if (!text || /^\[[^\]]*\]$/.test(text)) {
      line.innerHTML = rawHtml;
      return line;
    }
    var tokens = (pinyinLine || "").split(/\s+/).filter(Boolean);
    line.appendChild(buildRubyFragment(text, tokens));
    return line;
  }

  function mountLines(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return;
    var html = el.innerHTML;
    var pinyinField = el.getAttribute("data-pinyin") || "";
    var hanziLines = splitOnBr(html);
    var pinyinLines = pinyinField.split(/<br\s*\/?>/i).map(function (s) { return s.trim(); });
    el.innerHTML = "";
    for (var i = 0; i < hanziLines.length; i++) {
      var raw = hanziLines[i];
      if (!raw && !pinyinLines[i]) continue;
      el.appendChild(buildLineNode(raw, pinyinLines[i] || ""));
    }
  }

  window.songsRuby = {
    mountElement: mountElement,
    mountLines: mountLines,
  };
})();
