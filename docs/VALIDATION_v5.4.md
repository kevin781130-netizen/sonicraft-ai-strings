# SONICRAFT v5.4 Validation — Conductor-Steered Candidate Generation

Validated 2026-09-03 in the available Linux environment.

## v5.4 Core PASS

- Conductor Intent is built from D Original before candidate steering.
- A/B/C retain Conservative / Balanced / Expressive identities but are section-steered.
- D Original is never steered.
- Immutable note identity/timing/articulation fields are asserted unchanged.
- Dynamic steering is capped by the D-derived section Dynamic ceiling.
- Straight/non-vibrato anchors are not forced into vibrato.
- Bow Reserve metadata is recomputed after Bow Pressure steering.
- post-steer structural critic scores are recorded.
- `*.candidate_steering.json` is emitted.
- progressive candidate rendering is enabled.
- deferred candidates are escalated on low Audio Judge margin.
- downstream v5.2 Global Coherence, v5.3 Conductor Lock and merged-vs-D verification remain mandatory.
- no new MIDI CC / ParamID family.
- project state remains v13.

## Section steering regression PASS

Synthetic five-section performance:
- Climax primary budget: B / C / D, deferred A.
- Resolution primary budget: A / B / D, deferred C.

Observed steered mean Dynamics Energy:
- Climax B: ~0.7998
- Climax C: ~0.8186
- Resolution A: ~0.5121
- Resolution B: ~0.5212

C therefore explores a stronger Climax than B, while Resolution A remains no hotter than B.
All Climax C anchors remained at or below the D-derived Dynamic ceiling.

## Progressive candidate budget PASS

### High-confidence skip branch

A local fixture produced a confident primary-set winner.
Result:
- at least one deferred candidate was not rendered;
- `candidate_renders_skipped >= 1`;
- `candidate_renders_escalated = 0`;
- downstream Conductor Lock and merged-vs-D verification passed;
- observed test cost fraction vs four full renders: ~0.88 including final whole-song verification renders.

### Low-margin escalation branch

The primary Climax set B/C/D was deliberately made <0.025 apart.
Result:
- deferred A was rendered automatically;
- A became the local winner after escalation;
- `candidate_renders_escalated >= 1`;
- downstream Conductor Lock and whole-song pair verification passed.

This proves v5.4 reduces compute only when confidence permits; skipped candidates remain recoverable evidence.

## Compiler / intent stability PASS

The same MusicXML was compiled across Repair Policy generation 0 -> 1.
Stable D-derived Conductor Intent:
- section count: 5
- Climax section: 4
- intent hash: `e0354ada2c2677218504ffae`

v5.4 additionally verified:
- `candidate_steering.json` uses the same intent hash;
- Climax primary policy = B/C/D;
- Resolution primary policy = A/B/D;
- queue advertises progressive budgeting and deferred-candidate escalation;
- D Original never-steered contract is explicit.

## Regression PASS

- v5.3 Conductor Intent / macro lock
- v5.2 Global Performance Coherence
- v5.1 Selective Phrase Search
- v5.0 >45-second Shadow chunk/crossfade:
  - chunks: 2
  - frames: 404000
  - peak: ~0.023622
- v4.9 Repair Policy gates
- v4.8 Critic:
  - D 34.314
  - A 72.747
  - B 76.773
  - C 73.207
- v4.7 Phrase Torch/NumPy parity
- v4.6 Transition Torch/NumPy parity
- ORT no-Torch:
  - 12000 x 34
  - peak ~0.404252

## Native PASS

Clean VST-independent CMake configure/build completed to 100%.

Native PASS:
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
- intentional renderer tamper rejected with `renderer_binding_failed`

## Realtime-core non-regression

The following v5.4 files are byte-identical to packaged v5.3:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v5.4 therefore changes candidate generation / orchestration only.

## Integrity

- UIDESC XML parses.
- explicit numeric ParamID collisions: 0.
- highest explicit ParamID base: 740.
- project state: v13.
- installer/prebuilt includes:
  - conductor_candidate_steering_v54.py
  - compile_musicxml_strings_v54.py
  - auto_loop_strings_v54.py
  - COMPILE_MUSICXML_STRINGS_v54.bat
  - AUTO_LOOP_STRINGS_v54.bat

## Honest boundary

- Steering is a bounded deterministic control search, not a learned conductor model.
- Section Character labels remain deterministic performance-envelope labels, not formal musicological analysis.
- Candidate budgeting can save local renders but does not guarantee a fixed percentage reduction on every score.
- Deferred candidates are rendered when initial Audio margin is insufficient.
- No new acoustic training data or weights were added.
- No realtime acoustic renderer code was changed.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v5.4 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
