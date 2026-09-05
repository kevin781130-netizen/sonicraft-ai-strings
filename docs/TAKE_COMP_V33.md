# SONICRAFT v3.3 Phrase Take Comp

v3.3 adds a realtime-safe phrase comp layer above the v3.2 A/B/C/D Retake Carousel.

Workflow:
1. Set Host Scope to Locator Retake or Both.
2. Audition A/B/C/D manually or with Auto Loop.
3. Enable Take Comp = Phrase Comp.
4. When the current phrase sounds best, trigger Commit Current Phrase.
5. Move through the locator and commit a different take for another phrase.
6. Playback resolves each committed phrase to its chosen deterministic take; uncommitted phrases continue using the current audition take.

The comp table is fixed-size (128 entries), allocation-free in the audio path, and never edits authored MIDI. Clear Phrase Comp discards the transient comp map. Persistent serialization of the comp map is intentionally not claimed in v3.3; the mode and phrase length are saved, while the realtime phrase choices are session-runtime state pending a future host-safe chunk format.
