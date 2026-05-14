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
 *   attachAudioButton(buttonId, filename)   - wires a button to play `filename`
 *                                             via HTML5 <audio>, bypassing Anki
 *                                             autoplay. Pass a bare filename
 *                                             like `foo.mp3` (no `[sound:...]`
 *                                             wrapper — use the `soundfile:`
 *                                             template filter shipped in the
 *                                             addon to obtain it).
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

  function attachAudioButton(buttonId, filename) {
    var btn = document.getElementById(buttonId);
    if (!btn) return;
    filename = (filename || "").trim();
    console.log("ankiDecks audio: filename =", JSON.stringify(filename));
    if (!filename) {
      btn.disabled = true;
      btn.textContent = "No audio";
      return;
    }
    // If the filter add-on isn't installed, {{soundfile:Audio}} may have
    // returned the raw `[sound:foo.mp3]` token. Recover the filename so the
    // button at least works while the user installs the add-on.
    var m = filename.match(/\[sound:([^\]]+)\]/);
    if (m) {
      console.warn(
        "ankiDecks audio: got raw [sound:...] token — install the " +
        "chinese_anki_decks_nosound add-on to suppress autoplay."
      );
      filename = m[1];
    }
    // Encode unicode / spaces for URL resolution. Preserves path separators.
    var src = encodeURI(filename);
    var audio = new Audio(src);
    audio.preload = "auto";
    audio.addEventListener("error", function () {
      console.error(
        "ankiDecks audio: load error for src=" + audio.src,
        audio.error
      );
    });
    btn.title = "play: " + filename;
    btn.addEventListener("click", function () {
      console.log("ankiDecks audio: click play src=" + audio.src);
      try {
        audio.currentTime = 0;
        var p = audio.play();
        if (p && typeof p.catch === "function") {
          p.catch(function (err) {
            console.warn("ankiDecks audio: play() rejected:", err);
          });
        }
      } catch (err) {
        console.warn("ankiDecks audio: play() threw:", err);
      }
    });
  }

  window.ankiDecks = {
    mountRuby: mountRuby,
    attachToggle: attachToggle,
    mountExamples: mountExamples,
    attachAudioButton: attachAudioButton,
  };
})();
