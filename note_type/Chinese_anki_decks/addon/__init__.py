"""Anki add-on for the Chinese (anki-decks) note type.

Two responsibilities:

1. Template filters used by the card templates:
     {{soundfile:Audio}}   - returns just `foo.mp3` from `[sound:foo.mp3]`
                             (empty string if no sound ref present)
     {{nosound:Audio}}     - field text with every `[sound:...]` reference
                             stripped

   Neither emits a `[sound:...]` token, so Anki's autoplay scanner does not
   pick it up. The templates route all audio through HTML5 `<audio>` rather
   than Anki's native player so we can control volume centrally.

2. A volume control surfaced as a button in Anki's main top toolbar. Click
   opens a slider dialog (0–100%). The chosen value is persisted in the
   add-on's config and injected into every reviewer webview as
   `window.ankiDecksConfig.volume` (a float 0–1). `_ruby.js` reads that
   value when constructing audio elements, so changing the slider updates
   playback volume across every card after the next render.
"""

from __future__ import annotations

import re

from anki.hooks import field_filter
from aqt import gui_hooks, mw
from aqt.qt import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    Qt,
    QVBoxLayout,
)

SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")
DEFAULT_VOLUME = 70  # percent
CONFIG_KEY = "volume"


# ---------------------------------------------------------------------------
# Template filters

def _filter(field_text: str, field_name: str, filter_name: str, ctx) -> str:
    if filter_name == "soundfile":
        m = SOUND_RE.search(field_text)
        return m.group(1) if m else ""
    if filter_name == "nosound":
        return SOUND_RE.sub("", field_text).strip()
    return field_text


field_filter.append(_filter)


# ---------------------------------------------------------------------------
# Volume config

def _get_volume() -> int:
    cfg = mw.addonManager.getConfig(__name__) or {}
    try:
        v = int(cfg.get(CONFIG_KEY, DEFAULT_VOLUME))
    except (TypeError, ValueError):
        v = DEFAULT_VOLUME
    return max(0, min(100, v))


def _set_volume(value: int) -> None:
    cfg = mw.addonManager.getConfig(__name__) or {}
    cfg[CONFIG_KEY] = max(0, min(100, int(value)))
    mw.addonManager.writeConfig(__name__, cfg)


# ---------------------------------------------------------------------------
# Webview injection — every reviewer card render gets the current volume.

def _on_card_will_show(text: str, card, kind: str) -> str:
    vol = _get_volume() / 100.0
    snippet = (
        f'<script>window.ankiDecksConfig=Object.assign('
        f'window.ankiDecksConfig||{{}},{{volume:{vol:.3f}}});</script>'
    )
    return snippet + text


gui_hooks.card_will_show.append(_on_card_will_show)


# ---------------------------------------------------------------------------
# Top toolbar button + slider dialog

def _open_volume_dialog() -> None:
    dlg = QDialog(mw)
    dlg.setWindowTitle("Chinese Decks — Audio Volume")
    dlg.setMinimumWidth(320)
    layout = QVBoxLayout(dlg)

    current = _get_volume()
    label = QLabel(f"Volume: {current}%")
    layout.addWidget(label)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(current)
    slider.setTickInterval(10)
    slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    layout.addWidget(slider)

    def _on_change(v: int) -> None:
        label.setText(f"Volume: {v}%")

    slider.valueChanged.connect(_on_change)

    btn_row = QHBoxLayout()
    save_btn = QPushButton("Save")
    cancel_btn = QPushButton("Cancel")
    btn_row.addStretch(1)
    btn_row.addWidget(cancel_btn)
    btn_row.addWidget(save_btn)
    layout.addLayout(btn_row)

    def _save() -> None:
        _set_volume(slider.value())
        _refresh_toolbar()
        dlg.accept()

    save_btn.clicked.connect(_save)
    cancel_btn.clicked.connect(dlg.reject)
    save_btn.setDefault(True)

    dlg.exec()


def _on_toolbar_links(links, toolbar) -> None:
    label = f"🔊 {_get_volume()}%"
    links.append(
        toolbar.create_link(
            "chinese_decks_volume",
            label,
            _open_volume_dialog,
            tip="Chinese (anki-decks) — set audio volume",
            id="chinese_decks_volume",
        )
    )


def _refresh_toolbar() -> None:
    if mw and mw.toolbar:
        mw.toolbar.draw()


gui_hooks.top_toolbar_did_init_links.append(_on_toolbar_links)
