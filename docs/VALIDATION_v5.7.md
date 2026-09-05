# SONICRAFT v5.7 Validation — Context Generalization / Similarity Transfer

Validated 2026-09-03 in the available Linux environment.

## v5.7 Core PASS

- same-Section-Character transfer only
- Critic dimension overlap required
- minimum Jaccard similarity 0.34
- donor minimum aggregate Utility evidence gate
- donor v5.6 Audit risk blocks transfer
- target<-donor edge trust gate
- transfer evidence scale 0.32
- per-slot transferred evidence cap 4.0
- transferred evidence receives additional read-time discount
- transfer-only confidence cap < 0.72
- Top1+D requires >=1.5 actual target-context evidence
- exact Utility Memory remains actual-render-only
- transfer edge calibration is independent of donor exact-context memory
- no new MIDI CC / ParamID family
- project state remains v13

## Cold-target generalization regression PASS

Target:

`build|latent_playability+transition`

Target local evidence before run:

`0`

Accepted donors:

- `build|latent_playability`
- `build|transition`

Transfer-only prediction:

- transferred evidence: >=1.5
- confidence remained below 0.72
- initial render set: B / C / D
- pruned candidate: A
- actual local winner: B
- standard escalation: no
- counterfactual audit: not due

Result:

A completely cold exact context saved one local render while the downstream Audio Judge / Conductor / merged-vs-D safety chain remained active.

Fixture final cost:

~0.88 × the four-full-render reference.

The pruned A candidate received zero exact-target Utility evidence.

## Transfer-only Top1 guard PASS

Direct predictor regression:

- local evidence: 0
- transferred evidence: 4.0
- confidence: ~0.627627
- initial slots: A / B / D

Despite strong donor history, transfer-only evidence did not unlock Top1+D.

## Cross-context isolation PASS

Rejected:

- cross Section Character donor
- unrelated Critic dimension donor
- exact context key as "transfer" (exact evidence stays local)

Only same-character overlapping problem dimensions can lend evidence.

## Donor Audit risk gate PASS

A donor context with repeated v5.6 Counterfactual False-Prunes was disabled by its exact-context auditor.

Result:

- donor local Utility evidence remained present
- v5.7 transferred evidence from that donor: 0
- cold target returned to v5.4 primary budget

## Counterfactual transfer-edge calibration PASS

Transfer-assisted target predicted B and initially rendered B/C/D.

At deterministic counterfactual audit opportunity #12, pruned A was rendered and won:

- pre-audit winner: B
- full-evidence winner: A
- Counterfactual gain: ~+0.050000024 Overall
- False Prune: true

v5.7 updated only the two used transfer edges:

- `target <- build|latent_playability`: trust 1.0 -> 0.56
- `target <- build|transition`: trust 1.0 -> 0.56

Donor Utility B evidence was byte/value unchanged by this transfer failure.

This validates that the system learns "this analogy is unreliable" rather than "the donor itself was wrong."

## v5.6 -> v4.8 orchestration/source regression PASS

- v5.6 Counterfactual Auditor interval / false-prune / disable / recovery
- v5.6 hidden False-Prune audit: B -> A, gain ~0.050000024
- v5.5 Candidate Utility predictor
- v5.5 high-confidence Zero-Render
- v5.5 predictor/audio disagreement escalation
- v5.4 Conductor-Steered Candidate generation
- v5.3 Long-Form Conductor Intent
- v5.2 Global Performance Coherence
- v5.1 Selective Phrase Search / MIDI boundary merge
- v5.0 >45s Shadow chunk/crossfade: 2 chunks / 404000 frames
- v4.9 Repair Policy
- v4.8 Critic: D 34.314 / A 72.747 / B 76.773 / C 73.207
- v4.7 Phrase Torch/NumPy parity
- v4.6 Transition Torch/NumPy parity
- ORT no-Torch: 12000 x 34

## Native PASS

Clean VST-independent CMake configure/build completed to 100%.

Native PASS:

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
- SonicraftInProcessEngineSmoke: 9600 frames / 34 channels / peak ~0.0705933

## Promotion Guard PASS

- promotion binding PASS
- intentional renderer tamper rejected with `renderer_binding_failed`

## Realtime-core non-regression

The following v5.7 files are byte-identical to packaged v5.6:

- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v5.7 therefore changes pre-render evidence transfer / calibration only.

## Integrity

- UIDESC XML parses
- explicit numeric ParamID collisions: 0
- highest explicit ParamID base: 740
- project state: v13
- installer/prebuilt includes:
  - context_similarity_transfer_v57.py
  - compile_musicxml_strings_v57.py
  - auto_loop_strings_v57.py
  - COMPILE_MUSICXML_STRINGS_v57.bat
  - AUTO_LOOP_STRINGS_v57.bat

## Honest boundary

- Similarity is an interpretable Jaccard-based context rule, not a learned semantic embedding.
- Transfer does not create audio evidence; it only discounts already observed donor evidence.
- Transfer-only evidence cannot authorize maximum Top1+D pruning.
- Final sonic authority remains actual renders + Audio Judge and downstream guards.
- No new acoustic training data or weights were added.
- No realtime acoustic renderer code was changed.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v5.7 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
