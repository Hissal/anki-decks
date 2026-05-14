"""Anki add-on for the Chinese (anki-decks) note type.

Registers two template filters:

  {{soundfile:Audio}}   - returns just `foo.mp3` from `[sound:foo.mp3]`
                          (or empty string if no sound ref present)
  {{nosound:Audio}}     - returns the field text with every `[sound:...]`
                          reference stripped

Neither filter emits a `[sound:...]` token, so Anki's autoplay scanner does
not pick it up. Use this in front-side HTML when you want access to the
audio filename without triggering autoplay — e.g. the Hanzi recognition
card's Play Audio button reads `{{soundfile:Audio}}` and plays it via an
HTML5 <audio> element on click.
"""

from __future__ import annotations

import re

from anki.hooks import field_filter

SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")


def _filter(field_text: str, field_name: str, filter_name: str, ctx) -> str:
    if filter_name == "soundfile":
        m = SOUND_RE.search(field_text)
        return m.group(1) if m else ""
    if filter_name == "nosound":
        return SOUND_RE.sub("", field_text).strip()
    return field_text


field_filter.append(_filter)
