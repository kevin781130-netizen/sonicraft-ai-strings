# v0.3 changelog

- Added LASS/Chris-Hein-style **Single Section** workflow as the default, while retaining Q4 Multi CH1-4 mode.
- Added AI Performance Assist modes: Manual / Assist / Auto.
- Added AI Look Ahead parameter for future predictive-render integration.
- Preserved the 12-patch C0-B0 articulation bank and the fixed conventional CC map.
- Added Transition Speed, Short Tightness, and Attack Character as compact performance controls.
- Added the new controls to the neural renderer conditioning vector (9 -> 12 continuous frame controls).
- Added hard-MIDI-lock design rules: AI microperformance may not silently alter composition.
- Added commercial-safe 2025 CORA Good-sounds distribution (CC BY 4.0) as a separate provenance ID from the legacy CC BY-NC Zenodo copy.
- Added MID-FiLD (MIT, MIDI-only) for symbolic dynamics/control priors.
- Added optional FSD50K CC0-only bowed-string policy; disabled by default and never a final timbre anchor.
- Added Good-sounds CORA downloader/manifest scripts with fail-closed provenance messaging.
- Preview engine now responds to transition speed, short tightness, and attack character.
- Renderer compact size: 15,293,440 params (~29.17 MiB FP16); HQ: 33,118,208 params (~63.17 MiB FP16), excluding codec.
