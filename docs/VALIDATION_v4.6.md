# SONICRAFT v4.6 Validation — Continuous Transition & Legato

Validated 2026-09-02 in the available Linux environment.

## v4.6 PASS
- Continuous Transition Graph link classification
- same-string / cross-string Portamento modes
- same-bow / re-bow Legato modes
- gesture-anchor boundary reconciliation
- phrase-level CC38 window contract
- smooth written-pitch conditioning across connected notes
- second-note hard-onset suppression
- transition_target_ms population
- Legato/Transition continuity
- Vibrato envelope continuity
- Note Progress transition-head continuity
- v4.6 multi-note CC39 direct +/-50-cent float-pitch conditioning
- v4.5 single-note Gesture windows do NOT activate v4.6 transition path
- v4.6 compiler emits `.transition.json`
- no new MIDI CC / ParamID family
- Torch / NumPy transition-control parity

## Concrete transition smoke
A two-note 72 -> 79 MIDI phrase in one continuous CC38 window:
- produced one transition link
- populated transition_target_ms up to 123.6 ms
- suppressed the second hard onset
- produced continuous float pitch samples through the boundary
- re-centered generic pitchbend after applying lane-local CC39 micro-pitch directly to pitch conditioning

## Preview
- CC39 Preview scaling corrected to its documented +/-50-cent range while Shadow/HQ retains raw authored CC39.
- Continuous gesture Preview voices can inherit same-lane Vibrato phase/jitter state and partial envelope state.
- This code compiles in the full native build.
- Real host/auditory Preview-vs-HQ validation is not claimed without VST3 host build.

## v4.5 PASS
- Continuous Gesture Graph
- gesture interpolation
- MusicXML gesture compiler
- gesture Torch / NumPy parity
- v4.5 source/release regression remains forward-compatible

## v4.4 / v4.3 / v4.2 / v4.1 PASS
- Ensemble Bow & Phrase solver/runtime/compiler/parity
- String Constraint & Transition solver/compiler
- String Physical planner/compiler/runtime/parity
- Strings Score / 4x4 Voice compiler
- explicit String Voice HQ isolation

## v3.9 -> v3.0 PASS
- Preference-Guided Auto Comp source contract
- Judge Memory evidence/confidence
- legacy 100-byte / personal 144-byte protocol compatibility
- Audio-Aware Take Judge
- Smart Comp Timeline
- Performance Memory
- Persistent Phrase Comp
- Phrase Take Comp
- Retake Carousel
- Host Scope
- Host Command / Project Bridge
- Torch / NumPy performance-control parity
- ORT no-Torch 12000 x 34

## Native PASS
Full VST-independent CMake build completed.
Native executables PASS:
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
- SonicraftTempoSampleMapSmokeV37
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

v3.8 personal protocol also PASS:
- legacy Judge response = 100 bytes
- personal Judge response = 144 bytes
- evidence = 1.35

## Integrity
- UIDESC XML parses.
- explicit numeric ParamID bases: no collisions.
- highest explicit base remains 740; v4.6 adds no ParamID family.
- project state remains schema v13.
- installer/prebuilt contracts include:
  - string_transition_graph_v46.py
  - string_transition_runtime_v46.py
  - compile_musicxml_strings_v46.py
  - COMPILE_MUSICXML_STRINGS_v46.bat
- release fallback import probe now includes v4.3/v4.4/v4.5/v4.6 runtime modules.

## Honest boundary
- No new acoustic training data / weights were added.
- Continuous transition conditioning is not evidence of newly captured real transition samples.
- Vibrato envelope/Preview phase carry is not a claim of a newly trained phase-continuous acoustic model.
- More than four independent simultaneous voices per string part remain outside the current 4x4 bus.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v4.6 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
