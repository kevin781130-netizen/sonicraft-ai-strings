# v4.2 Changelog — String Physical Performance

- Added deterministic String Physical Performance Graph for strings only.
- Added per-note playable string/fingering path, hand position, shift distance and open-string inference.
- Added phrase-aware bow direction/change planning with MusicXML up-bow/down-bow override.
- Added bow pressure and contact-point priors.
- Added explicit/inferred portamento route and stable divisi desk identity.
- Added editable Physical MIDI Bus: CC27/28/29/30/31/33/34/35. CC32 remains unused because it is Bank Select LSB.
- Added 16-lane VST parameter families for the Physical Bus.
- Preview/HQ physical residuals are opt-in and field-presence aware; legacy/no-physical MIDI does not inherit fake defaults.
- Bow Change now affects HQ bow-change probability only at note onset.
- Audio Judge config identity now includes all per-lane expression and physical state.
- Added v4.2 MusicXML/XML/MXL compiler and one-click BAT.
- Runtime/prebuilt installer gates include all v4.2 compiler/physical modules.
- Project state remains v13; note physical state is authored MIDI/Score Graph data.
- No new training data, acoustic weights or unsupported technique claims.
