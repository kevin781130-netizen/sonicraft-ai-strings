# SONICRAFT v5.3 Validation — Long-Form Conductor Intent / Section Character Lock

Validated 2026-09-03 in the available Linux environment.

## v5.3 Core PASS

- deterministic macro section extraction
- 2–8 section bounded segmentation
- Section Character labels:
  - Intro
  - Build
  - Sustain
  - Climax
  - Release
  - Resolution
- stable D-derived Conductor Intent hash
- climax section / normalized climax position
- Dynamic mean / peak / ceiling
- Vibrato depth / rate palette
- Bow pressure / reserve floor
- Desk looseness
- Transition density / treatment
- per-part Lead / Inner / Foundation role distribution
- Section Character score gate
- hard climax-shift lock
- hard premature Dynamic ceiling lock
- hard long-line direction reversal lock
- hard role-lock loss detection
- bounded near-scoring candidate search
- tiny Section Character prior
- v5.2 Global Coherence remains a prerequisite
- v5.2 merged-vs-D full Audio verification remains mandatory
- no new MIDI CC / ParamID family
- project state remains v13

## Concrete macro-intent regression

Synthetic five-section performance:

1. Intro dynamic mean ~0.449
2. Build ~0.549
3. Build ~0.609
4. Climax ~0.789
5. Resolution ~0.529

Extracted:
- intended Climax = Section 4

A local test made C the Audio winner, but C pushed the pre-climax section beyond the macro envelope.
The v5.3 search selected B instead:

- Local winner: C
- Selected: B
- Conductor Intent score: 100.0
- Search combinations: 3
- Conductor override: PASS

## Coherence-PASS / Conductor-FAIL regression

Three adjacent pre-climax sections were lifted together so phrase-to-phrase continuity remained smooth.

Result:
- v5.2 Global Coherence: PASS
- Coherence score: ~93.58 in the diagnostic case
- v5.3 Conductor Intent: FAIL
- detected:
  - `climax_shift_S4_to_S3`
  - `long_line_direction_reversal_S3_S4`

This proves v5.3 is not a duplicate of v5.2.

A bounded candidate search where D was locally unsafe produced:
- searched: 2
- v5.2 coherence-passing combinations: 2
- v5.3 intent-passing combinations: 0
- result: explicit fallback required

## Intent hash stability PASS

The same MusicXML was compiled before and after Repair Policy generation changed 0 -> 1.

Stable across both compiles:
- section count: 5
- climax section: 4
- section boundaries
- Section Character labels
- intent hash: `e0354ada2c2677218504ffae`

Therefore A/B/C learning cannot move the D-derived long-form target.

## v5.3 Auto-loop integration PASS

Selective local-repair fixture:
- local A/B/C/D Judge PASS
- Global Coherence PASS
- Conductor Intent PASS
- conductor lock sidecar written
- intent hash propagated through search/trace
- merged-vs-D whole-song pair verification PASS
- pair Overall delta: ~+0.040
- final mode: `selective_conductor_lock`

## v5.2 -> v4.8 source regressions PASS

- v5.2 public release/version contract
- v5.1 Selective Phrase source contract
- v5.0 Local Shadow Auto-Loop source contract
- v4.9 Repair Iteration source contract
- v4.8 Critic source contract

Runtime/behavior regressions PASS:
- v5.1 selective phrase search + coverage fallback
- v5.1 selective MIDI merge boundary protection
- v5.0 >45 second Shadow chunk/crossfade:
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

The following v5.3 files are byte-identical to packaged v5.2:

- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v5.3 therefore changes score/performance macro planning and orchestration only.

## Integrity

- UIDESC XML parses
- explicit numeric ParamID collisions: 0
- highest explicit ParamID base: 740
- project state: v13
- installer/prebuilt includes:
  - conductor_intent_v53.py
  - compile_musicxml_strings_v53.py
  - auto_loop_strings_v53.py
  - COMPILE_MUSICXML_STRINGS_v53.bat
  - AUTO_LOOP_STRINGS_v53.bat

## Honest boundary

- Section labels are deterministic performance-envelope labels, not formal musicological form recognition.
- Conductor Intent is extracted from D Original; it does not compose a new interpretation.
- The tiny Section Character prior only breaks near-ties inside the Audio drop gate.
- No new acoustic training data or weights were added.
- No realtime acoustic renderer code was changed.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v5.3 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
