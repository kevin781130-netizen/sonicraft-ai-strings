# SONICRAFT v5.6 Validation — Counterfactual Render Auditor / False-Prune Self-Calibration

Validated 2026-09-03 in the available Linux environment.

## v5.6 Core PASS

- deterministic per-context prune-opportunity counter
- stable audit interval = 12
- elevated-risk interval = 6
- high-risk interval = 4
- disabled-context interval = 1
- False-Prune margin = 0.025 Overall
- Safety floor = 0.35
- Overall floor = 0.35
- near-miss tracking below the False-Prune threshold
- recent False-Prune Rate
- predictor confidence multiplier
- confidence degradation to Top2+D or v5.4 primary budget
- per-context Zero-Render disable
- fast disable: 2 False Prunes in latest 4 audits
- stable disable: >=4 recent audits and FPR >=25%
- four-clean-audit recovery
- deterministic clean-history reset on recovery
- actual-render-only Utility Memory boundary preserved
- no new MIDI CC / ParamID family
- project state remains v13

## Scheduled hidden-winner regression PASS

A high-confidence v5.5 context was pre-trained to expect B.

Hypothetical initial render set:
- B = 0.90
- D = 0.64

This is a healthy Audio margin and agrees with the predictor, so normal v5.5 safety escalation would NOT run.

The context was advanced to prune opportunity 12. v5.6 scheduled a counterfactual audit and rendered the otherwise-pruned A/C slots.

Full evidence:
- A = ~0.95 after WAV round-trip
- B = ~0.90
- C = ~0.68
- D = ~0.64

Result:
- hypothetical v5.5 winner: B
- full-evidence winner: A
- counterfactual gain: ~+0.050000024
- False Prune: TRUE
- standard v5.5 escalation: FALSE
- counterfactual audit expansion: TRUE
- final local winner: A

This proves v5.6 catches a blind spot that low-margin and predictor/audio-disagreement gates cannot detect.

Audit fixture total render cost was ~1.007 of the four-full-render baseline because the scheduled audit intentionally repurchased all candidate evidence.

## Disable / recovery regression PASS

Stable context:
- opportunities 1–11: no audit
- opportunity 12: audit

After repeated audit failures:
- two False Prunes in latest four audits -> Zero-Render disabled for that context
- audit interval -> 1
- predictor confidence multiplier reduced
- initial scheduling falls back to the v5.4 primary budget

Recovery:
- four consecutive clean audits
- context re-enabled
- clean recovery streak becomes the new recent calibration window
- recent FPR returns to 0 in the regression fixture
- stable interval returns to 12

## v5.5 regression PASS

High-confidence Zero-Render fixture remains unchanged:
- initial render: predicted best + D
- at least two candidates skipped
- no standard escalation
- skipped A/C receive no fake Utility Memory evidence
- final cost fraction: ~0.75

Predictor/audio disagreement fixture remains unchanged:
- predictor expected B
- actual initial winner disagreed
- every pruned candidate restored
- full local winner A

## v5.4 / v5.3 / v5.2 regression PASS

v5.4:
- Climax B/C ~0.7998 / 0.8186
- Resolution A/B ~0.5121 / 0.5212
- skip fixture cost ~0.88
- escalation fixture cost ~1.0

v5.3:
- five-section macro intent
- Section 4 Climax
- local C -> conductor-selected B
- Coherence-PASS / Conductor-FAIL regression still detects:
  - climax_shift_S4_to_S3
  - long_line_direction_reversal_S3_S4

v5.2:
- incoherent local A rejected
- near-scoring B selected
- coherence ~99.4176

## Earlier runtime regression PASS

- v5.1 Selective Phrase Search + coverage fallback
- v5.1 MIDI merge boundary protection
- v5.0 >45 s chunk/crossfade:
  - chunks: 2
  - frames: 404000
- v4.9 Repair Policy memory/gates
- v4.8 Critic:
  - D 34.314
  - A 72.747
  - B 76.773
  - C 73.207
- v4.7 Phrase Torch/NumPy parity:
  - max Vibrato Rate 5.7 Hz
  - depth 23.433 cents
- v4.6 Transition Torch/NumPy parity:
  - target ~129.72 ms
- ORT no-Torch:
  - 12000 x 34
  - peak ~0.404252

## Native PASS

Clean VST-independent CMake configure/build completed to 100%.

Native PASS:
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

The following v5.6 files are byte-identical to the packaged v5.5 release:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v5.6 therefore changes render-scheduling calibration only.

## Integrity

- explicit numeric ParamID collisions: 0
- highest explicit ParamID base: 740
- project state: v13
- installer/prebuilt includes:
  - counterfactual_auditor_v56.py
  - compile_musicxml_strings_v56.py
  - auto_loop_strings_v56.py
  - COMPILE_MUSICXML_STRINGS_v56.bat
  - AUTO_LOOP_STRINGS_v56.bat

## Honest boundary

- Counterfactual auditing measures the current objective Audio Judge, not human perceptual truth.
- An audit intentionally costs extra render compute on the audited opportunity.
- False-Prune statistics are context-local and depend on accumulated actual renders.
- No new acoustic training data or weights were added.
- No realtime acoustic renderer code was changed.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v5.6 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
