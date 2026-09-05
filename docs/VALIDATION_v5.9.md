# SONICRAFT v5.9 Validation — Multi-Archetype Mixture / Soft Classification

Validated 2026-09-03 in the available Linux environment.

## v5.9 Core PASS

- soft mixture of up to three Performance Archetype prototypes
- softmax distance weighting
- component minimum weight 0.08
- weights re-normalize to 1.0
- mixture confidence floor 0.42
- mixture-only Top-1 + D prohibition
- target-local evidence required for Top-1 + D
- weighted actual-render-only component learning
- skipped candidate no-learning across all mixture components
- weight-aware component->context Counterfactual calibration
- v5.8 hard-archetype trust isolation
- v5.7 Similarity Transfer edge isolation
- v5.5 exact Utility isolation
- no new MIDI CC / ParamID family
- project state remains v13

## Boundary-profile fixture

Synthetic control-profile distances:

- Intimate: 0.120
- Ballad: 0.135
- Chamber: 0.225
- Cinematic: 0.360
- Dramatic: 0.430

v5.9 soft mixture:

- Intimate: 0.447476
- Ballad: 0.387907
- Chamber: 0.164617
- mixture confidence: 0.812155

Weights sum to 1.0.

This demonstrates that a boundary profile is represented as a mixture rather than forced into one label.

## Cold-start Auto-Loop regression

Target:
`build|latent_playability+transition`

Starting state:
- exact Utility evidence: 0
- v5.7 Similarity Transfer evidence: 0
- cross-song aggregate Archetype evidence available for Intimate and Ballad components

v5.9 produced:
- mixture evidence: 1.85181
- reason: `soft_archetype_mixture_top2_plus_D`
- initial local render budget: B / C / D
- A: Zero-Render
- actual local winner: B
- no standard escalation
- no Counterfactual Audit in the clean fixture
- downstream Conductor Lock: PASS
- merged-vs-D pair verification: PASS
- total fixture cost: ~0.88 of four-full-render reference

Mixture-only evidence did not unlock Top-1 + D.

## Weighted rendered-only learning

For a mixture containing Intimate / Ballad / Chamber:
- only actually rendered slots receive evidence
- skipped B/C in the unit fixture remain byte-for-byte/numerically unchanged in every component memory
- component learning weight follows mixture component weight

No unrendered candidate is treated as a loser.

## Hidden False-Prune regression

Initial mixture-based budget:
- B / C / D rendered
- A pruned

On the deterministic Counterfactual Audit opportunity:
- pre-audit winner: B
- hidden pruned winner: A
- counterfactual gain: 0.050000024

v5.9 component trust after the False Prune:

- Intimate: 0.80311056
- Ballad: 0.82932092
- Chamber: 0.92756852

The dominant component receives the strongest penalty.

Isolation checks:
- v5.8 hard-archetype trust: unchanged
- v5.7 transfer edge count: unchanged / 0 in the fixture
- v5.5 exact Utility evidence: not penalized

## Backward regressions PASS

v5.8:
- Archetype cold-start Top-2 + D
- hidden False-Prune calibration
- release and source contracts

v5.7:
- Similarity Transfer
- donor high-risk audit block
- edge isolation

v5.6:
- Counterfactual interval / false-prune / disable / recovery
- hidden B -> A audit
- audit fixture cost ~1.007

v5.5:
- high-confidence Zero-Render
- cost ~0.754
- predictor/audio disagreement escalation
- cost ~1.007

v5.4:
- Conductor Steering
- Climax B/C distinction
- Resolution A/B restraint
- progressive budget skip ~0.88

v5.3:
- 5-section Long-Form Conductor Intent
- intended Climax Section 4
- local C -> selected B
- Intent score 100.0

v5.2:
- Global Coherence substitution
- bad A score 48.027754
- selected B
- coherence 99.4176

v5.1:
- Selective Phrase search / coverage fallback
- MIDI merge boundary protection

v5.0:
- >45 second Shadow chunk/crossfade
- 2 chunks
- 404000 frames
- transient renderer startup failure occurred once in this environment; isolated rerun PASS

v4.9:
- Repair Policy PASS

v4.8:
- Critic / Repair:
  - D 34.314
  - A 72.747
  - B 76.773
  - C 73.207

v4.7:
- Phrase Torch/NumPy parity
- max rate 5.7 Hz
- depth 23.433 cents

v4.6:
- Transition Torch/NumPy parity
- target ~129.72 ms

ORT no-Torch:
- 12000 x 34
- peak ~0.404252

## Release-contract forward compatibility PASS

Public release/version contracts v5.0 through v5.8 accept the current v5.9 public surface while continuing to verify their historical files and runtime modules.

Source contracts verified:
- v5.8
- v5.7
- v5.6
- v5.5
- v5.4
- v5.3
- v5.2
- v5.1

## Native PASS

Clean VST-independent CMake configure/build completed to 100%.

Native PASS:
- SonicraftArchetypeMixtureSmokeV59
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

The following v5.9 files are byte-identical to packaged v5.8:

- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v5.9 therefore changes only compiler/orchestration/control-memory behavior.

## Integrity

- UIDESC XML parses
- explicit numeric ParamID collisions: 0
- highest explicit ParamID base: 740
- project state: v13
- installer/prebuilt includes:
  - archetype_mixture_v59.py
  - compile_musicxml_strings_v59.py
  - auto_loop_strings_v59.py
  - COMPILE_MUSICXML_STRINGS_v59.bat
  - AUTO_LOOP_STRINGS_v59.bat

## Honest boundary

- Archetype labels and mixtures are performance-control prototypes, not formal genre recognition.
- Mixture weights are deterministic control-distance priors, not learned embeddings.
- No new acoustic training data or weights were added.
- No realtime acoustic renderer code was changed.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v5.9 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
