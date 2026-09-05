# SONICRAFT v4.5 Validation — Continuous String Gesture Graph

Validated 2026-09-02 in the available Linux environment.

## v4.5 gesture PASS
- seven gesture anchors per bowed note
- expressive swell / accent decay / legato arc / tremolo energy / flautando air / portamento arc / sustain breathe profiles
- pizzicato does not receive fake bow curves
- bounded micro-pitch planning
- `.gesture.json` sidecar
- CC38 Gesture Amount / opt-in window
- CC39 lane-local Micro Pitch
- HQ linear interpolation of authored voice-control snapshots
- HQ linear interpolation of physical-control curves
- Torch / NumPy control-path parity with gesture enabled
- legacy no-CC38 path remains non-interpolated
- Audio Judge identity includes Gesture Amount + lane-local Micro Pitch

## Compiler PASS
- MusicXML -> v4.5 MIDI / score / constraints / ensemble / gesture sidecars
- Type-1 / PPQ960 / five tracks
- repeated CC22/23/24/25/31/33/34 curve anchors
- CC38 window open/close
- CC39 lane-local micro-pitch anchors

## Renderer / protocol PASS
- v4.5 gesture service protocol: 12000 frames / 34 channels
- v4.4 ensemble timing protocol regression: 12000 / 34
- v4.1 encoded String Voice protocol regression: 12000 / 34
- v2.2 multi-out regression: 12000 / 34
- v3.7 Judge protocol regression

## Native PASS
- clean VST-independent CMake build
- v4.5 String Gesture native smoke
- v4.4 Ensemble native smoke
- v4.3 Constraint native smoke
- v4.2 Physical native smoke
- v4.1 Expression native smoke
- in-process engine: 9600 frames / 34 channels
- v3.9 -> v2.7 native regression smokes

## Backward compatibility PASS
- v4.4 Ensemble Torch/NumPy parity with no Gesture marker
- v4.2 Physical Torch/NumPy parity
- v3.9 Preference Auto Comp source contract
- v3.7 Audio Judge source contract
- v3.6 Smart Timeline source contract
- v3.5 Performance Memory source contract
- v3.4 Persistent Comp source contract
- v3.3 Phrase Comp source contract
- v3.2 Retake Carousel source contract
- v3.1 Host Scope source contract
- v3.0 Host Command / Project Bridge source contracts
- v2.9 Performance Compiler
- v2.8 Performance Commander
- ORT no-Torch path: 12000 x 34

## Integrity
- project state remains schema v13
- explicit numeric ParamID bases contain no duplicates
- v4.5 generated ranges:
  - 720..735 Gesture Amount
  - 740..755 Micro Pitch
  do not overlap prior generated ranges
- UIDESC XML parses
- installer/prebuilt contracts include v4.5 graph/runtime/compiler and BAT

## Honest boundary
- Bow Speed / Kinetic Response are planning/control dimensions mapped into existing model controls; no new measured bow-speed training was added.
- Planner micro-pitch normally stays far inside the wider +/-50-cent editable CC39 contract.
- Preview receives discrete MIDI anchors; HQ renderer performs the continuous interpolation. Host-validated Preview sub-anchor interpolation is not claimed.
- no new acoustic training data or weights were added.
- true per-string/desk timbre, col legno/sul ponticello/sul tasto and other unavailable acoustic techniques still require acoustic evidence/data.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here; rebuilt v4.5 VST3, Validator, Cubase and Studio One host validation are NOT claimed.
