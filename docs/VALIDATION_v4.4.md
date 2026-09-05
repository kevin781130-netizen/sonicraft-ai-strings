# SONICRAFT v4.4 Validation — Ensemble Bow & Phrase

Validated 2026-09-02 in the available Linux environment.

## v4.4 ensemble PASS
- cross-part onset clustering
- per-lane phrase segmentation
- compatible bow-direction synchronization
- explicit up/down-bow conflict preservation + warning
- ensemble bow-change anchors
- deterministic part/desk attack spread
- phrase-end breathing
- lead / inner / foundation role metadata
- `.ensemble.json` sidecar
- DAW conductor markers for ensemble conflicts
- CC36 signed Attack Offset compile
- CC37 Phrase Breath compile
- runtime attack/release timing execution
- Torch / NumPy timing parity
- Audio Judge config identity includes ensemble timing state

## Renderer / protocol PASS
- v4.4 ensemble timing renderer-service protocol: 12000 frames / 34 channels
- v4.1 encoded String Voice protocol regression: 12000 / 34
- v2.2 multi-out regression: 12000 / 34
- v3.7 Judge protocol regression

## v4.3 / v4.2 / v4.1 PASS
- v4.3 constraint solver / transition repair / bow budget / stop-divisi logic
- v4.2 physical planner/runtime/compiler + Torch/NumPy parity
- v4.1 Score/Voice compiler + explicit String Voice HQ isolation
- historical source/release contracts forward-compatible

## v3.9 -> v2.8 PASS
- Preference-Guided Auto Comp
- Judge Memory
- Audio-Aware Take Judge
- Smart Comp Timeline
- Performance Memory
- Persistent Comp / Phrase Comp
- Retake Carousel
- Host Scope / Host Command / Project Bridge
- DAW-native Performance Compiler
- Performance Commander
- ORT no-Torch path: 12000 x 34

## Native PASS
- full VST-independent CMake build
- v4.4/v4.3/v4.2/v4.1 native smokes
- v3.9 -> v2.8 native regression smokes
- in-process engine: 9600 frames / 34 channels
- Promotion Guard + tamper rejection
- Realtime / Low-Latency / Standalone targets build

## Integrity
- project state remains schema v13
- explicit numeric ParamID bases collision-free
- v4.4 adds only:
  - 680..695 CC36
  - 700..715 CC37
- UIDESC XML parses
- installer/prebuilt includes v4.4 solver/runtime/compiler/BAT

## Honest boundary
- ensemble coordination is deterministic performance planning, not a trained conductor model.
- Preview approximates timing; HQ renderer executes actual ms offsets.
- no new acoustic training data or weights.
- real per-string/desk timbre and recorded section interaction still require acoustic evidence.
- >4 independent simultaneous voices per string part remain outside the current 4x4 bus.
- no Steinberg VST3 SDK / target DAW toolchain here, so rebuilt v4.4 VST3, Validator,
  Cubase host validation and Studio One host validation are NOT claimed.
