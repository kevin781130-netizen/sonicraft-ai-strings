# SONICRAFT v3.9 Validation

Validated on 2026-09-01 in the available Linux environment.

## v3.9 Preference-Guided Auto Comp — PASS
- Source contract for unresolved-only Locator scan, one asynchronous Audio Judge in flight, Confidence / winner-Margin / Safety gates, Cancel, and one final `commitBatch`.
- Accepted candidates are accumulated and committed once, preserving one internal Undo snapshot.
- Auto-committed decisions are explicitly excluded from preference learning, preventing self-reinforcement.
- `SonicraftPreferenceAutoCompSmokeV39` native gate smoke PASS.

## v3.8 Judge Memory / Personal Taste — PASS
- Local 5-dimension profile: Dynamics, Attack, Transition, Stability, Safety.
- One manual Commit evidence sample: evidence `1.35`, confidence approximately `0.0986`.
- Safety preference is constrained non-negative; personalized correction is bounded to +/-0.12 around the objective Judge.
- v3.7 legacy Judge client remains wire-compatible at exactly 100 bytes.
- v3.8 personalized Judge response is exactly 144 bytes.
- Local profile JSON survives Renderer Service restart; restart query recovered evidence `1.35` and confidence approximately `0.0986`.
- Multi-instance stale-result guard is source-contract validated through profile identity matching.
- `SonicraftPreferenceClientSmokeV38` PASS.

## Commercial packaging blocker fixed — PASS
The v3.7 Renderer Service imports `audio_take_judge_v37.py`, but older Runtime/prebuilt allowlists could omit it. v3.9 source contracts require both:
- `audio_take_judge_v37.py`
- `judge_memory_v38.py`

in the Runtime installer, release installer, prebuilt collector, and prebuilt-layout verifier.

## Backward regression — PASS
- v3.7 Audio-Aware Take Judge source + DSP smoke.
- v3.6 Smart Comp Timeline.
- v3.5 Performance Memory.
- v3.4 Persistent Performance Comp / state alignment.
- v3.3 Phrase Take Comp.
- v3.2 Retake Carousel.
- v3.1 Host Locator Scope.
- v3.0 Command Lane / Project Bridge.
- v2.9 DAW-native Performance Compiler.
- v2.8 Performance Commander.
- v2.7 portable RNG.
- Native in-process engine: 9600 frames, 34 channels, peak approximately 0.0705933.
- Promotion Guard + tamper rejection.
- Mock Renderer client PASS.
- Mock Renderer multi-out: 12000 x 34, peak approximately 0.024.
- Torch / NumPy performance-control parity PASS.
- ORT no-Torch backend: 12000 x 34 PASS.

## Build / state / UI checks — PASS
- Clean VST-independent CMake build.
- SDK-independent `shadow_render_client.cpp` compile.
- SDK-independent `preference_client_v38.cpp` compile.
- Project state schema v13; Controller accepts and consumes v13 in the matching order.
- Explicit ParamID scan: no duplicate numeric IDs; current explicit maximum is 363.
- UIDESC XML parses successfully.

## Release boundary — NOT CLAIMED
The current environment does not contain the Steinberg VST3 SDK or the target Windows/macOS DAW toolchains. Therefore the following are still release gates and are **not** claimed as PASS:
- rebuilt v3.9 VST3 binary;
- Steinberg Validator;
- Cubase host validation;
- Studio One host validation;
- real host UI/output-parameter validation;
- save/close/reopen project validation with the rebuilt v3.9 plug-in;
- signed commercial installer.

No training data or acoustic model weights were changed in v3.8/v3.9.
