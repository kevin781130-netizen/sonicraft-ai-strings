# SONICRAFT v3.6 Validation

Validated 2026-09-01 in the available Linux environment.

## PASS — v3.6 Smart Comp Timeline
- 8-phrase timeline window / cursor windowing
- per-slot persistent Committed Take status
- per-slot Smart Pick status
- deterministic Smart Rank
- Conservative / Balanced / Adventurous variation priority
- actual A/B/C/D derived Retake nonce -> renderer-equivalent 8-bit nonce quantization
- target-aware Retake dimension/salt selection
- MIDI Authority Lock exclusion for Micro-Pitch ranking
- Favorite dominates ranking
- Reject excludes candidate
- all-four-Rejected returns no suggestion
- Smart Audition / Smart Commit source contract
- Commit Unique Favorites source contract
- Heuristic Auto Comp Unresolved source contract
- fixed-memory batch commit + Undo/Redo regression

## PASS — compatibility / engine regression
- v3.5 Performance Memory
- v3.4 Persistent Performance Comp
- v3.3 Phrase Take Comp
- v3.2 deterministic Retake Carousel
- v3.1 Host Locator Scope
- v3.0 Host Command Lane and Project Bridge
- v2.9 DAW-native Performance Compiler
- v2.8 Performance Commander
- Torch / NumPy performance-control parity
- ORT no-Torch backend: 12000 x 34
- native in-process engine: 9600 frames / 34 channels
- portable RNG
- Promotion Guard + tamper rejection
- Mock renderer single-output client
- Mock renderer multi-out: 12000 x 34
- clean VST-independent CMake build
- UIDESC XML parse
- explicit public ParamID duplicate scan

## State / release convergence
- Processor state schema: v12
- Controller accepts schema v12 and consumes Smart Rank Mode before comp payload
- v10/v11 persistent comp migration retained
- Smart Rank Mode is persistent; timeline is derived and creates no duplicate project-state source of truth
- VERSION / Manager / Prebuilt Builder / installer defaults / prebuilt manifest metadata converged to `3.6.0-smart-comp-timeline`

## Important semantic boundary
Smart Rank is a deterministic **candidate-priority heuristic**, not audio-quality inference. It does not claim to know which rendered take sounds best without listening to audio or a trained preference model.

## Release boundary
The Steinberg VST3 SDK and target Windows/macOS DAW toolchains are not present in this environment. Therefore the following are NOT claimed as PASS here:
- rebuilt v3.6 VST3 binary;
- Steinberg Validator on that binary;
- real Cubase / Studio One 8-phrase timeline rendering;
- Processor -> Controller status propagation in a loaded host;
- save -> close -> reopen host persistence on the rebuilt v3.6 binary.

No acoustic weights or training data changed.
