# Archived templates

Card templates retired from the active word-deck note type but kept for
reference and as a recovery path.

## `audio_recognition_front.html` / `audio_recognition_back.html`

Original Card 2 of the word-deck note type: **Audio recognition**. Audio
autoplayed on the front with hanzi hidden behind a "Show Hanzi" reveal
button. Retired because:

1. The card depended entirely on TTS quality. When the synthesized
   pronunciation mispronounced a syllable or sounded subtly off, the
   card became ungradeable — you couldn't tell whether the failure was
   your recognition or the audio.
2. The current 3-card layout replaces it with a scaffolded
   **Audio + Written intro** card (see `../intro_front.html` /
   `../intro_back.html`). Audio still gets exposure on the intro card's
   autoplay; the standalone listening drill was dropped from the default
   deck.

A future opt-in, tag-gated audio-only card type is captured in the
repo-root `TODO.md`. If you want listening drill back in your deck,
either restore these templates manually in Anki or wait for the gated
implementation.

These files are not loaded by anything in the active codebase. Deleting
them would lose the recovery path and the historical record of the
design.
