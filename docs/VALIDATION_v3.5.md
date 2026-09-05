# SONICRAFT v3.5 Validation

Validated 2026-09-01 in the available Linux environment.

## PASS
- v3.5 Performance Memory C++ smoke
  - Locator window / wrap navigation
  - Next Unresolved
  - coverage calculation
  - Favorite/Reject live status
  - review-only metadata does not silently commit
  - Clear Phrase restores unresolved state
- v3.5 Processor/Controller source contract
  - state schema v11
  - v10 -> v11 old entries migrate committed=true
  - v11 review-only entries carry an explicit committed flag
  - browser follow / recall / cursor serialized before comp payload
  - Processor read-only status output parameter wiring
- Exact Locator-end regression fixed: an end exactly on a phrase boundary no longer includes the next phrase.
- v3.4 Persistent Comp regression
- v3.3 Phrase Comp regression
- v3.2 Retake Carousel regression
- v3.1 Host Scope regression
- v3.0 Command Lane / Project Bridge regression
- v2.9 Performance Compiler regression
- v2.8 Performance Commander regression
- Torch / NumPy performance-control parity
- ORT no-Torch backend: 12000 x 34
- Mock Renderer client
- Mock Renderer multi-out: 12000 x 34
- Native in-process engine: 9600 frames / 34 channels
- Portable RNG regression
- Promotion Guard + tamper rejection
- Clean VST-independent CMake build
- UIDESC XML parse

## Fixed in this pass
- Favorite/Reject can exist without committing the reviewed take.
- v3.4 Commit Across Locator endpoint could include one extra phrase at exact boundaries.
- v3.4 expanded UIDESC/editor constraint mismatch could clip the new controls.

## Release boundary
Steinberg VST3 SDK and target Windows/macOS DAW toolchains are not present here. Therefore a rebuilt v3.5 VST3 binary and real Cubase/Studio One UI/status/save-reopen validation are NOT claimed. Those remain release gates.

No acoustic weights or training data changed.
