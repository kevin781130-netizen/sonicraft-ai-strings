# SONICRAFT v5.8 Validation — Cross-Song Performance Archetype Memory

Validated 2026-09-03 in the available Linux environment.

## v5.8 Core PASS

- five fixed performance-control prototypes:
  - Intimate
  - Ballad
  - Dramatic
  - Chamber
  - Cinematic
- deterministic D-derived aggregate feature extraction
- classification confidence + secondary label
- low-confidence classification hard block (< 0.42)
- persistent Archetype Memory
- memory key: Archetype + Section Character + Critic Context
- actual-render-only learning
- skipped-candidate no-learning
- archetype-only Top-1 + D prohibition
- cold-start Top-2 + D acceleration
- Counterfactual false-prune calibration
- archetype->context edge isolation
- no new MIDI CC / ParamID family
- project state remains v13

## Cold-start Archetype Memory regression

A synthetic Intimate-like D control envelope classified:

- label: Intimate
- confidence: 0.727061

With:
- target local Utility evidence = 0
- v5.7 Similarity Transfer evidence = 0
- only cross-song Archetype history available

v5.8 produced:
- reason: `archetype_cross_song_top2_plus_D`
- initial slots: A / B / D
- Archetype evidence: 2.410739
- pure Archetype evidence did not unlock Top-1 + D

Low-confidence classification (0.30) with the same stored history produced:
- Archetype evidence = 0
- reason: low archetype confidence

## Full Auto-Loop cross-song regression

Build context:
- exact Utility evidence = 0
- v5.7 transfer evidence = 0
- Archetype = Intimate
- classification confidence = 0.82

Historical Archetype memory was populated using only actually rendered B/C/D observations.

v5.8 changed the first local render budget:

- v5.4 baseline: A / B / C / D
- v5.8: B / C / D
- A: Zero-Render
- actual Audio winner: B
- no standard escalation
- no counterfactual audit in the clean case
- downstream Conductor Lock PASS
- merged-vs-D full pair verification PASS
- fixture total cost: ~0.88 of the four-full-render reference

The target exact Utility memory learned only rendered slots. The pruned candidate remained untouched.

## Hidden false-prune audit regression

The same Archetype prior predicted B/C/D and pruned A.

Counterfactual Audit was primed to its deterministic 12th prune opportunity.

Actual audio:
- pre-audit winner: B
- hidden pruned winner: A
- counterfactual gain: 0.050000024

Result:
- False Prune = TRUE
- archetype->context trust: 1.0 -> 0.56
- v5.7 Similarity Transfer edge count remained 0
- final local winner became A
- downstream full pair verification PASS

This proves Archetype calibration is isolated from v5.7 transfer memory.

## v5.7 -> v4.x regressions PASS

- v5.7 Similarity Transfer:
  - cold target saved one local render
  - transfer-only confidence ~0.627627
  - target<-donor false-prune edge trust -> 0.56
  - donor high-risk audit block PASS
- v5.6 Counterfactual Auditor:
  - 12-opportunity audit cadence
  - hidden B->A false prune caught
  - disable/recovery PASS
  - audit fixture cost ~1.007
- v5.5 Candidate Utility:
  - high-confidence Zero-Render cost ~0.754
  - predictor/audio disagreement escalation ~1.007
- v5.4 Conductor Steering:
  - Climax B/C control separation PASS
  - Resolution A/B restraint PASS
  - candidate-budget skip fixture ~0.88
- v5.3 Conductor Intent:
  - five-section fixture
  - Climax = Section 4
  - local C -> selected B
  - Intent score 100
- v5.2 Global Coherence:
  - bad A score 48.027754
  - coherent B selected
  - coherence 99.4176
- v5.1 Selective Phrase:
  - coverage fallback regression PASS
- v5.0 >45 second chunk:
  - 2 chunks
  - 404000 frames
- v4.9 Repair Policy PASS
- v4.8 Critic:
  - D 34.314
  - A 72.747
  - B 76.773
  - C 73.207
- v4.7 Phrase Torch/NumPy parity:
  - max rate 5.7 Hz
  - depth 23.433 cents
- v4.6 Transition Torch/NumPy parity:
  - target ~129.72 ms
- ORT no-Torch:
  - 12000 x 34
  - peak ~0.404252

## Native PASS

Clean VST-independent CMake configure/build completed to 100%.

Native PASS:
- SonicraftPerformanceArchetypeSmokeV58
- SonicraftContextSimilarityTransferSmokeV57
- SonicraftCounterfactualAuditorSmokeV56
- SonicraftCandidateUtilitySmokeV55
- SonicraftConductorSteeringSmokeV54
- SonicraftConductorIntentSmokeV53
- SonicraftGlobalCoherenceSmokeV52
- SonicraftSelectivePhraseSmokeV51
- SonicraftStringRepairPolicySmokeV49
- SonicraftStringPerformanceCriticSmokeV48
- SonicraftStringPhraseSmokeV47
- SonicraftStringTransitionSmokeV46
- SonicraftStringGestureSmokeV45
- SonicraftStringEnsembleSmokeV44
- SonicraftStringConstraintSmokeV43
- SonicraftStringPhysicalSmokeV42
- SonicraftStringExpressionSmokeV41
- SonicraftInProcessEngineSmoke:
  - 9600 frames
  - 34 channels
  - peak ~0.0705933

## Promotion Guard PASS

- promotion binding PASS
- intentional tamper rejected with `renderer_binding_failed`

## Realtime-core non-regression

The following v5.8 files are byte-identical to packaged v5.7:

- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v5.8 therefore changes only score/control-memory/orchestration behavior.

## Integrity

- UIDESC XML parses
- explicit numeric ParamID collisions: 0
- highest explicit ParamID base: 740
- project state: v13
- installer/prebuilt includes:
  - performance_archetype_memory_v58.py
  - compile_musicxml_strings_v58.py
  - auto_loop_strings_v58.py
  - COMPILE_MUSICXML_STRINGS_v58.bat
  - AUTO_LOOP_STRINGS_v58.bat

## Honest boundary

- Archetype labels are fixed performance-control prototypes, not formal genre recognition.
- Persistent Archetype Memory is cross-song capable but does not persist song identity, so it does not count unique songs.
- Archetype evidence influences render budgeting only; it does not retrain the acoustic model.
- No new acoustic training data or weights were added.
- No realtime renderer code was changed.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v5.8 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
