# SONICRAFT v5.2 Validation — Global Performance Coherence Guard

Validated 2026-09-03 in the available Linux/source environment.

## v5.2 Global Coherence PASS
- Baseline-relative whole-piece coherence analysis
- Dynamic trajectory
- Vibrato character (depth + phrase rate)
- Bow energy (pressure + reserve)
- Desk looseness / ensemble attack spread
- Transition density / treatment
- Section role distribution (lead / inner / foundation)
- Local winner / near-runner / D bounded candidate search
- v5.1 `phrase:<id>` and v5.2 internal phrase-key compatibility
- D Original retained as an explicit safety candidate
- Global Coherence JSON sidecar

Concrete substitution regression:
- local Audio winner: A = 0.900
- near runner-up: B = 0.875
- A whole-piece Coherence score: 48.027754 (rejected)
- selected B Coherence score: 99.4176 (accepted)
- search combinations evaluated: 3

This verifies that a locally stronger candidate can be rejected when it creates a new whole-piece performance discontinuity, while a near-scoring coherent candidate may be substituted.

## Full Merged-vs-D Pair Verification PASS
At selective convergence v5.2 renders:
1. selective merged full song
2. D Original full song

Each render is judged against its own MIDI intent.

Acceptance gate:
- Merged Overall >= D Overall - 0.025
- Merged Safety >= D Safety - 0.04

Positive regression:
- pair verify Overall delta: +0.04
- Global Coherence PASS
- selective merged output accepted

Failure regression:
- local repair / Global Coherence stage passed
- merged-vs-D Overall delta: -0.20
- pair gate failed
- full A/B/C/D fallback triggered
- final full fallback winner: B
- Repair Policy generation remained 1; stale R1 queue did not learn twice

## v5.1 Selective Repair Regression PASS
- Selective Phrase Search
- critic + repair-location search
- coverage fallback
- local Shadow context render
- local-vs-full context sample equivalence: max error 0.0
- selective MIDI merge boundary protection
- accepted local-repair branch
- low-confidence local -> full A/B/C/D fallback
- v5.1 source/release contracts remain valid under forward v5.2 public version

The v5.1 accepted regression measured 0.757 of four-full-render cost on its fixture. v5.2 adds one extra D full-song verification render, so compute savings are deliberately smaller in exchange for whole-piece safety; short synthetic fixtures may exceed a 1.0 cost fraction because local-context overhead dominates.

## v5.0 Auto-Loop Regression PASS
- compiled MIDI -> Shadow events -> mock service WAV
- >45 second chunk/crossfade path: 2 chunks, 404000 frames in regression fixture
- automatic low-confidence stop / review artifact
- accepted R1 -> R2 -> WINNER orchestration
- v5.0 source/release contracts remain valid

## v4.9 / v4.8 Regression PASS
v4.9:
- Repair Policy memory and gates
- Audio Judge -> learn -> R2
- stale replay rejection
- candidate-specific MIDI Judge intent

v4.8:
- structural Performance Critic
- A/B/C repair fanout + D Original
- compiler / Judge Queue
- structural diagnostic regression remains:
  D 34.314 / A 72.747 / B 76.773 / C 73.207

## v4.7 -> v4.1 Strings Regression PASS
- v4.7 Phrase Torch/NumPy parity: max vibrato rate 5.7 Hz, depth 23.433 cents fixture
- v4.6 Transition Torch/NumPy parity
- v4.5 Continuous Gesture source contract
- v4.4 Ensemble Bow & Phrase source contract
- v4.3 String Constraint / Transition source contract
- v4.2 Physical Torch/NumPy parity + source contract
- v4.1 4x4 String Voice source contract
- v3.0 Torch/NumPy performance-control parity
- ORT no-Torch path: 12000 x 34

## Historical Release Contracts PASS
Forward-compatible release contracts pass for:
- v5.1
- v5.0
- v4.9
- v4.8
- v4.7
- v4.6
- v4.5
- v4.4
- v4.3
- v4.2
- v4.1

Legacy runtime/module presence checks were retained; only current public-version acceptance was made forward-compatible.

## Clean Native Build PASS
External clean CMake build:
- SONICRAFT_BUILD_VST3=OFF
- SONICRAFT_BUILD_PRODUCT_SHELL=OFF
- build completed to 100%

Native smokes PASS:
- SonicraftGlobalCoherenceSmokeV52
- SonicraftSelectivePhraseSmokeV51
- SonicraftStringShadowAutoLoopSmokeV50
- SonicraftStringRepairPolicySmokeV49
- SonicraftStringPerformanceCriticSmokeV48
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
- SonicraftTempoSampleMapSmokeV37
- SonicraftInProcessEngineSmoke: 9600 frames / 34 channels, peak 0.0705933

## Promotion Guard PASS
- promotion binding PASS
- intentional tamper rejected with `renderer_binding_failed`

## Realtime / Acoustic Core Non-Regression
The following v5.2 files are byte-identical to packaged v5.1:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

Therefore v5.2 changes graph/orchestration safety logic, not the realtime acoustic core.

## Integrity / Release Surface
- UIDESC XML parses
- explicit numeric ParamID bases: no collisions
- highest explicit ParamID base: 740
- project state remains schema v13
- no new MIDI CC family
- no new ParamID family
- v5.2 runtime import probe PASS
- installer/prebuilt require:
  - global_performance_coherence_v52.py
  - compile_musicxml_strings_v52.py
  - auto_loop_strings_v52.py
  - COMPILE_MUSICXML_STRINGS_v52.bat
  - AUTO_LOOP_STRINGS_v52.bat

## Honest Boundary
- Global Coherence is a deterministic engineering/performance prior, not a human perceptual model.
- Full merged-vs-D Audio Judge is an engineering/adherence guard, not proof of human preference.
- No new acoustic training data or weights were added.
- No realtime renderer/model code was changed from v5.1.
- v5.2 source validation does not equal a rebuilt commercial VST3 binary.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable in this environment.
- Rebuilt v5.2 VST3, Steinberg Validator, real Cubase host validation, real Studio One host validation, signed installer, and commercial binary release approval are NOT claimed.
