# SONICRAFT v4.7 Validation — Phrase Bow & Vibrato Continuity

Validated 2026-09-02 in the available Linux environment.

## v4.7 PASS
- phrase-chain extraction from v4.6 transition links
- phrase contour classification
- long-line Dynamic Energy arc
- phrase Bow Energy reserve
- pressure/contact long-line shaping
- Vibrato Depth continuity
- non-zero Vibrato Rate target
- CC38=1/127 backward-compatible sentinel
- v4.6 files without the sentinel remain unchanged
- `.phrase.json` sidecar
- v4.7 compiler / MIDI sentinel output
- Torch / NumPy phrase-control parity
- NumPy and Torch expose `vibrato_physics_known` when v4.7 rate data is present
- no new MIDI CC or ParamID family
- project state remains v13

## Concrete v4.7 smokes
- phrase graph: 4-note arch, apex energy 1.08
- phrase runtime: max vibrato rate 5.70 Hz
- phrase runtime: max vibrato depth 21.78 cents
- Torch / NumPy parity: max vibrato rate 5.70 Hz, max depth 23.433 cents
- compiler: CC38 stream contains sentinel value 1 and one phrase-close zero

## v4.6 -> v4.1 regressions PASS
- Continuous Transition Graph
- transition pitch path / onset suppression / transition_target_ms
- v4.5 legacy transition gate
- Continuous String Gesture
- Ensemble Bow & Phrase
- Constraint / Transition Solver
- Physical Performance Graph
- 4x4 String Voice / Score Graph

## v3.9 -> v3.0 PASS
- Preference-Guided Auto Comp source contract
- Judge Memory
- Audio-Aware Take Judge
- Smart Comp Timeline
- Performance Memory
- Persistent / Phrase Comp
- Retake Carousel
- Host Scope
- Host Command / Project Bridge
- Torch / NumPy performance-control parity
- ORT no-Torch 12000 x 34

## Native PASS
Clean VST-independent CMake configure/build completed.
Native executables PASS:
- SonicraftStringPhraseSmokeV47
- SonicraftStringTransitionSmokeV46
- SonicraftStringGestureSmokeV45
- SonicraftStringEnsembleSmokeV44
- SonicraftStringConstraintSmokeV43
- SonicraftStringPhysicalSmokeV42
- SonicraftStringExpressionSmokeV41
- SonicraftPreferenceAutoCompSmokeV39
- SonicraftPreferenceClientSmokeV38
- SonicraftTakeJudgeProtocolSmokeV37
- SonicraftSmartCompTimelineSmokeV36
- SonicraftPerformanceMemorySmokeV35
- SonicraftPersistentTakeCompSmokeV34
- SonicraftTakeCompSmokeV33
- SonicraftRetakeCarouselSmokeV32
- SonicraftHostCycleScopeSmokeV31
- SonicraftHostCommandLaneSmokeV30
- SonicraftPerformanceCommanderSmokeV28
- SonicraftParityRngSmokeV27
- SonicraftInProcessEngineSmoke: 9600 frames / 34 channels
- SonicraftInProcessPromotionGuardSmoke + tamper rejection
- Realtime / Low-Latency / Standalone targets build

## Renderer-service PASS
One current renderer service accepted:
- v4.5 Gesture protocol: 12000 / 34
- v4.4 Ensemble timing protocol: 12000 / 34
- v4.1 String Voice protocol: 12000 / 34
- v2.2 Multiout: 12000 / 34
- v3.7 Judge protocol
- legacy smoke client

## Integrity
- UIDESC XML parses.
- explicit numeric ParamID bases have no collisions.
- highest explicit ParamID base remains 740.
- v4.7 adds no ParamID family.
- project state remains schema v13.
- installer/prebuilt includes v4.7 graph/runtime/compiler/BAT.
- release fallback import probe includes v4.7 modules.

## Honest boundary
- Phrase arcs and bow reserve are deterministic performance priors, not measured bow centimeters.
- Vibrato rate/depth conditioning does not mean a new violinist-specific vibrato acoustic model was trained.
- No new acoustic training data or weights were added.
- More than four independent simultaneous voices per string part remain outside the current 4x4 bus.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v4.7 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
