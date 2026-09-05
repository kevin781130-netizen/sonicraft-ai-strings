# SONICRAFT v3.4 Validation

Validated on 2026-09-01 in the available Linux build environment.

## PASS
- v3.4 Persistent Phrase Comp standalone C++ smoke
  - commit / lookup
  - Favorite / Reject mutual exclusion
  - Undo / Redo
  - Commit Range
  - export / restore of take + review metadata
- v3.4 Processor/Controller state-layout source contract
  - Processor schema v10
  - Controller accepts v10
  - Controller consumes the v10 comp payload before part controls
  - invalid comp count / take index / masks fail closed
- v3.3 Phrase Take Comp regression
- v3.2 deterministic Retake Carousel regression
- v3.1 Host Locator Scope regression
- v3.0 Host Command Lane regression (CC102–119)
- v2.8 Performance Commander regression
- v2.7 portable RNG regression
- v2.6 Promotion Guard + tamper rejection
- Native in-process engine: 9600 frames / 34 channels
- Clean VST-independent CMake build
- UIDESC XML parse

## Important boundary
The Steinberg VST3 SDK and target Windows/macOS host toolchains are not installed in this environment. Therefore:
- a rebuilt v3.4 VST3 binary is NOT claimed;
- actual Cubase/Studio One save → close → reopen project persistence is still a release-gate test;
- host-native undo stack integration is NOT claimed. v3.4 provides its own fixed-memory 16-step comp Undo/Redo.

No acoustic model weights or training data were changed.
