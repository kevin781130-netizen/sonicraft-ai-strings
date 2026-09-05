# SONICRAFT v4.3 Validation — String Constraint & Transition Solver

Validated in the available Linux environment.

## v4.3 solver PASS
- future-aware string/fingering transition analysis
- explicit transition-repair regression
- configured instrument range violation reporting
- finite bow-budget tracking
- forced bow-change insertion before estimated exhaustion
- adjacent-string double-stop feasibility
- feasible double-stop consolidation into shared desk/bow state
- infeasible stop remains divisi
- 3/4-note geometry remains conservatively divisi
- >4 simultaneous independent voice overload detection
- DAW conductor marker generation for constraint issues
- `.constraints.json` sidecar generation
- Type-1 / PPQ960 / five-track compiler output

## v4.2 / v4.1 regressions PASS
- physical planner/runtime
- physical MIDI compiler
- physical Torch/NumPy parity
- 4×4 String Voice score/compiler
- explicit String Voice HQ isolation
- encoded String Voice renderer protocol: 12000 frames / 34 channels
- no new v4.3 ParamID family; v4.2 physical bus reused
- project state remains v13

## v3.9 and earlier regressions PASS
- Preference-Guided Auto Comp source contract
- Judge Memory evidence/confidence smoke
- v3.8 personal protocol: legacy 100-byte + personal 144-byte response compatibility
- v3.7 Audio Judge protocol
- v3.6 Smart Comp Timeline
- v3.5 Performance Memory
- v3.4 Persistent Comp
- v3.3 Phrase Comp
- v3.2 Retake Carousel
- v3.1 Host Scope
- v3.0 Host Command / Project Bridge
- v2.9 Performance Compiler
- v2.8 Performance Commander
- ORT no-Torch path: 12000 × 34

## Native PASS
- clean VST-independent CMake configure/build
- v4.3 String Constraint native smoke
- v4.2 String Physical native smoke
- v4.1 String Expression native smoke
- v3.9 Preference Auto Comp
- v3.8 Preference Client
- v3.7 Judge Protocol
- v3.6 Smart Timeline
- v3.5 Performance Memory
- v3.4 Persistent Comp
- v3.3 Phrase Comp
- v3.2 Carousel
- v3.1 Host Scope
- v3.0 Host Command
- v2.8 Commander
- v2.7 RNG
- in-process engine: 9600 frames / 34 channels
- Promotion Guard + tamper rejection

## Integrity
- UIDESC XML parses.
- explicit numeric ParamIDs contain no duplicate values.
- v4.3 adds no new realtime ParamID family.
- installer/prebuilt source contracts require:
  - string_constraint_solver_v43.py
  - compile_musicxml_strings_v43.py
  - COMPILE_MUSICXML_STRINGS_v43.bat

## Honest boundary
- Constraint rules are conservative ergonomic heuristics, not biomechanical proof.
- No new acoustic training data or weights were added.
- Double-stop feasibility does not mean a new dedicated double-stop acoustic model exists.
- Real per-string timbral differences still require acoustic evidence/data.
- More than four independently-expressed simultaneous notes per string part remain outside the current 4×4 bus.
- Steinberg VST3 SDK and target DAW toolchains are unavailable here; rebuilt v4.3 VST3 / Validator / real Cubase and Studio One validation are NOT claimed.
