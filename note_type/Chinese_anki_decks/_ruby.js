/*
 * anki-decks ruby builder + audio helpers.
 *
 * Place this file inside Anki's `collection.media` folder. Card templates
 * include it via `<script src="_ruby.js">`. The leading underscore tells
 * Anki not to clean it up as unused media.
 *
 * Volume is read from `window.ankiDecksConfig.volume` (float, 0–1). The
 * addon under note_type/Chinese_anki_decks/addon/ injects that into every
 * reviewer page render based on its config; if it's missing for any reason
 * we fall back to FALLBACK_VOLUME.
 *
 * Exposes `window.ankiDecks` with:
 *   mountRuby(containerId, { revealed })   - builds <ruby> from data-hanzi + data-pinyin
 *   attachToggle(containerId, buttonId)     - wires the toggle-pinyin button
 *   mountExamples(selector)                 - turns Examples field into <ul><li> ...
 *   attachAudioButton(buttonId, filename)   - click-to-play HTML5 audio button
 *   mountAutoplayAudio(selector)            - on each matching element, reads
 *                                             data-soundfile, autoplays the
 *                                             audio, renders a replay button.
 *                                             Also wires the R key to replay.
 */
(function () {
  "use strict";

  var FALLBACK_VOLUME = 0.7;

  // Matches one CJK character. Mirrors HAN_RE in scripts/common.py.
  var HAN_RE = /[㐀-䶿一-鿿]/;

  function isHan(ch) {
    return HAN_RE.test(ch);
  }

  function currentVolume() {
    var cfg = window.ankiDecksConfig;
    if (cfg && typeof cfg.volume === "number") {
      return Math.max(0, Math.min(1, cfg.volume));
    }
    return FALLBACK_VOLUME;
  }

  function buildRuby(hanzi, pinyinTokens) {
    var frag = document.createDocumentFragment();
    var tokenIdx = 0;
    var hanCount = 0;
    for (var i = 0; i < hanzi.length; i++) {
      hanCount += isHan(hanzi[i]) ? 1 : 0;
    }
    if (hanCount !== pinyinTokens.length) {
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

  // Hint format spec: each <br>-separated line may begin with "<card-type>:"
  // (case-insensitive, optional whitespace around the colon) to scope it to
  // one card. Recognized card types are intro / hanzi / audio / production.
  // ("audio" is retained for the archived audio-recognition template; the
  // active deck no longer emits an audio-only card by default.)
  // Mirrors HINT_CARD_TYPES + HINT_PREFIX_RE in scripts/common.py.
  var HINT_CARD_TYPES = { intro: 1, hanzi: 1, audio: 1, production: 1 };
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

  // Build the labeled hint DOM tree as a DocumentFragment. Uses textContent
  // for field data and a real <br> element for line breaks, so user-supplied
  // Hint values can never inject script/markup even though the deck is
  // #html:true. Mirrors the textContent-only treatment used by mountExamples
  // and buildRuby for other field content.
  function buildHintBody(parsed) {
    var frag = document.createDocumentFragment();
    var label = document.createElement("span");
    label.className = "hint-label";
    label.textContent = "Hint:";
    frag.appendChild(label);
    frag.appendChild(document.createTextNode(" "));
    var text = document.createElement("span");
    text.className = "hint-text";
    var parts = String(parsed).split(/<br\s*\/?>/i);
    for (var i = 0; i < parts.length; i++) {
      if (i > 0) text.appendChild(document.createElement("br"));
      text.appendChild(document.createTextNode(parts[i]));
    }
    frag.appendChild(text);
    return frag;
  }

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
        // Empty after filtering → no UI. Hide rather than leave empty so
        // the .hint-mount class's margin/padding doesn't leave a visible gap.
        el.style.display = "none";
        continue;
      }

      var revealed = el.dataset.revealed === "true";
      if (revealed) {
        el.classList.add("hint-revealed");
        el.textContent = "";
        el.appendChild(buildHintBody(parsed));
      } else {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "hint-btn";
        btn.textContent = "Show hint";
        (function (e, p) {
          btn.addEventListener("click", function () {
            e.classList.add("hint-revealed");
            e.textContent = "";
            e.appendChild(buildHintBody(p));
          });
        })(el, parsed);
        el.appendChild(btn);
      }
    }
  }

  function _makeAudio(filename) {
    filename = (filename || "").trim();
    if (!filename) return null;
    // Recover from a raw [sound:foo.mp3] token in case the soundfile: filter
    // is unavailable (addon missing) — the button at least works as a
    // fallback while the user sorts the addon install.
    var m = filename.match(/\[sound:([^\]]+)\]/);
    if (m) {
      console.warn(
        "ankiDecks audio: raw [sound:...] token reached client — install " +
        "the chinese_anki_decks_nosound add-on to suppress autoplay."
      );
      filename = m[1];
    }
    var src = encodeURI(filename);
    var audio = new Audio(src);
    audio.preload = "auto";
    audio.volume = currentVolume();
    audio.addEventListener("error", function () {
      console.error("ankiDecks audio: load error src=" + audio.src, audio.error);
    });
    return audio;
  }

  function _play(audio) {
    if (!audio) return;
    try {
      audio.volume = currentVolume();
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
  }

  function attachAudioButton(buttonId, filename) {
    var btn = document.getElementById(buttonId);
    if (!btn) return;
    var audio = _makeAudio(filename);
    if (!audio) {
      btn.disabled = true;
      btn.textContent = "No audio";
      return;
    }
    btn.title = "play: " + filename;
    btn.addEventListener("click", function () { _play(audio); });
  }

  // Most-recently-mounted autoplay audio. R-key replay targets this so the
  // hotkey behavior matches what users expect from Anki's native player.
  var lastAutoplayAudio = null;

  function mountAutoplayAudio(selector) {
    var nodes = document.querySelectorAll(selector);
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      if (node.dataset.ankiMounted === "1") continue;
      node.dataset.ankiMounted = "1";

      var filename = node.getAttribute("data-soundfile") || "";
      var audio = _makeAudio(filename);
      if (!audio) {
        node.textContent = "";
        continue;
      }

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "replay-btn";
      btn.setAttribute("aria-label", "Replay audio");
      btn.title = "Replay audio (R)";
      btn.innerHTML = "▶";
      (function (a, b) {
        b.addEventListener("click", function () { _play(a); });
      })(audio, btn);

      node.textContent = "";
      node.appendChild(btn);

      lastAutoplayAudio = audio;
      _play(audio);
    }
  }

  // Anki's R hotkey replays audio when the native player owns it. We bind
  // our own listener so the same hotkey works for our HTML5 audio.
  document.addEventListener("keydown", function (e) {
    if ((e.key === "r" || e.key === "R") && !e.ctrlKey && !e.metaKey && !e.altKey) {
      if (lastAutoplayAudio) {
        e.preventDefault();
        _play(lastAutoplayAudio);
      }
    }
  });

  window.ankiDecks = {
    mountRuby: mountRuby,
    attachToggle: attachToggle,
    mountExamples: mountExamples,
    attachAudioButton: attachAudioButton,
    mountAutoplayAudio: mountAutoplayAudio,
    parseHint: parseHint,
    mountHint: mountHint,
  };
})();
