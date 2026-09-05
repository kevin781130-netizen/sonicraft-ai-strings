# SONICRAFT v4.1 Validation — Strings Per-Note Expression

Validated 2026-09-01 in the available Linux environment.

## v4.1 Strings / Score PASS
- MusicXML / XML semantic Score Graph
- compressed MXL rootfile parsing
- Type-1 MIDI / PPQ960 / five tracks
- tempo changes, time-signature changes and key signatures
- chords, voice/staff identity, tie merge and slur intent
- base string articulation + four-bit Expression Stack
- 4x4 String Voice Bus:
  - Vln I: CH1,5,6,7
  - Vln II: CH2,8,9,10
  - Viola: CH3,11,12,13
  - Cello: CH4,14,15,16
- lane CC21..26 compile and controller mapping
- same-part overlapping notes retain independent base articulation / stack / dynamics
- PreviewEngine explicit voice-lane independence
- HQ renderer event protocol preserves part + voice_lane identity
- packed articulation low nibble remains trained base ID; high nibble is control stack
- explicit voice lanes receive independent deterministic Retake identities
- Torch / NumPy control-path parity after packed articulation changes
- fifth simultaneously-overlapping independently-expressed note creates deterministic
  `string_voice_lane_overflow` warning rather than an infinite-polyphony claim
- unavailable string techniques such as col legno / sul ponticello / sul tasto are preserved
  as semantic warnings rather than silently mapped to unsupported acoustic content
- MusicXML pizzicato direction is recognized from both text and `<sound pizzicato="yes/no">`

## Renderer / native PASS
- encoded String Voice renderer-service protocol: 12000 frames / 34 channels
- legacy renderer client regression
- legacy multi-out regression: 12000 x 34
- v3.7 Judge protocol regression
- clean VST-independent CMake build
- v4.1 StringExpression native smoke
- v3.9 Preference Auto Comp native smoke
- v3.8 PreferenceClient native smoke
- v3.7 Judge protocol native smoke
- v3.6 Smart Timeline native smoke
- v3.5 Performance Memory native smoke
- v3.4 Persistent Comp native smoke
- v3.3 Phrase Comp native smoke
- v3.2 Carousel native smoke
- v3.1 Host Scope native smoke
- v3.0 Command Lane native smoke
- v2.8 Performance Commander native smoke
- v2.7 portable RNG regression
- native in-process engine: 9600 frames / 34 channels
- Promotion Guard + tamper rejection

## Python/runtime regressions PASS
- v4.1 source / packaging contract
- v4.1 public-version convergence
- v3.9 Preference Auto Comp source contract
- v3.8 Judge Memory
- v3.7 Audio Judge
- v3.6 Smart Timeline
- v3.5 Performance Memory
- v3.4 Persistent Comp
- v3.3 Phrase Comp
- v3.2 Retake Carousel
- v3.1 Host Scope
- v3.0 Project Bridge / Host Command contract
- v2.9 Performance Compiler
- v2.8 Performance Commander
- ORT no-Torch backend: 12000 x 34

## Integrity
- UIDESC XML parses successfully.
- explicit numeric ParamIDs contain no duplicate values.
- v4.1 generated voice-control ranges are source-contract checked against legacy ranges.
- project state remains schema v13. Per-note expression is carried by editable MIDI / Score Graph.

## Honest boundary
- v4.1 provides four independently-expressed overlapping voices per string part, not
  Instrument X's advertised infinite-scale polyphony.
- no new string acoustic samples / training data / weights were added.
- preserved unsupported technique semantics do not mean those techniques have a true acoustic render.
- the current 16 stage aux feeds remain virtual geometry, not sixteen recorded microphones.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are not present in this environment.
  A rebuilt v4.1 VST3, Steinberg Validator, and real Cubase / Studio One host validation are NOT claimed.
- VST3 Note Expression and ARA are not implemented in this pass; v4.1 achieves note-level string
  independence with the backward-compatible 4x4 MIDI String Voice Bus.
