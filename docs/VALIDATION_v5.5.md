# SONICRAFT v5.5 Validation — Candidate Utility Predictor / Zero-Render Pruning

Validated 2026-09-03 in the available Linux environment.

## v5.5 core PASS
- explainable candidate utility predictor
- Section Character + localized Critic dimensions + post-steer structural scores + Repair Policy inputs
- local aggregate Utility Memory
- actual-render-only learning
- skipped candidates never learn
- D Original always rendered
- low/no-history fallback to v5.4 budget
- medium-confidence top-two repairs + D capability
- high-confidence top-one repair + D capability
- low Audio margin escalation
- predictor-vs-Audio winner disagreement escalation
- Safety / Overall escalation
- no new MIDI CC / ParamID family
- state remains v13

## High-confidence Zero-Render regression PASS
After 10 actual-render evidence updates in the same context, the predictor reached confidence 1.0 and predicted margin ~0.2245.
The first local pass rendered only B + D; A/C were not rendered.
Fixture compute fraction including mandatory final whole-song pair verification: ~0.754 of the four-full-render reference.

## Disagreement recovery PASS
The predictor expected B. Actual initial rendered evidence favored D with a healthy margin.
Because predictor and Audio winner disagreed, A/C were restored before acceptance. A then became the actual local winner.
All A/B/C/D were present after escalation.
Fixture compute fraction: ~1.007, demonstrating that safety can intentionally spend the saved budget back.

## Memory integrity PASS
- no-history => v5.4 primary budget
- high-history Resolution example => A + D first pass
- skipped B/C evidence unchanged
- only rendered A/D evidence advanced
- no audio/MIDI/score text/filenames stored

## Regression PASS
- v5.4 Conductor-Steered Candidate generation
- v5.3 Conductor Intent
- v5.2 Global Coherence
- v5.1 Selective Phrase Search
- v4.9 Repair Policy
- v4.8 Critic: D 34.314 / A 72.747 / B 76.773 / C 73.207
- ORT no-Torch: 12000 x 34, peak ~0.404252

## Native PASS
Clean VST-independent CMake configure/build completed to 100%.
PASS: v5.5 Candidate Utility, v5.4 Steering, v5.3 Intent, v5.2 Coherence, v5.1 Selective, v4.9 Policy, v4.8 Critic, v4.7 Phrase, v4.6 Transition, v4.5 Gesture, v4.4 Ensemble, v4.3 Constraint, v4.2 Physical, v4.1 Voice.
Native Engine: 9600 frames / 34 channels / peak ~0.0705933.

## Promotion Guard PASS
Intentional tamper rejected with `renderer_binding_failed`.

## Realtime-core non-regression
Byte-identical to packaged v5.4:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp / processor.h
- src/controller.cpp
- src/ids.h

## Honest boundary
The Utility Predictor is an evidence scheduler, not a perceptual model. It cannot establish that an unrendered candidate would lose; therefore all pruning is reversible through explicit escalation. No acoustic training data or weights were added. Rebuilt v5.5 VST3, Steinberg Validator, Cubase host validation and Studio One host validation are not claimed in this environment.
