# SONICRAFT v5.0 Validation — Local Shadow Render Auto-Loop

Validated 2026-09-03 in the available Linux environment.

## v5.0 orchestration PASS
- existing Renderer Service TCP protocol reused
- no direct Torch/ORT backend bypass in auto-render client
- compiled MIDI -> full String Voice Shadow event reconstruction
- keyswitch + Expression Stack packing
- voice control snapshots
- physical CC27-35 -> Shadow opcodes 112-119
- ensemble CC36/37 -> opcodes 120/121
- gesture CC38 -> opcode 122
- lane-local CC39 micro-pitch preserved
- ready existing service reuse
- local service auto-start when absent
- only self-spawned service is terminated
- model/service readiness failure is a hard stop

## Long render PASS
Renderer Service rejects one render request above 45 seconds by design.

A real TCP mock-service regression rendered a 50-second MIDI through v5.0:
- sample rate: 8 kHz test fixture
- output frames: 404000
- chunks: 2
- chunk size: 40 seconds
- overlap: 0.75 seconds
- output peak: 0.023622
- result: PASS

Every chunk receives the full event history; output stereo is overlap/crossfade assembled.

## Fully automatic TCP smoke PASS
A real TCP mock-service run completed:
- MusicXML -> v5.0 A/B/C/D compile
- local service start
- A/B/C/D Shadow render
- candidate-specific Audio Judge
- conservative stop gate
- final status: `review_required`
- REVIEW_BEST MIDI/WAV emitted
- decision trace emitted

This proves the loop does not force additional rounds when confidence is insufficient.

## Accepted multi-round branch PASS
A separate deterministic synthetic-WAV orchestration fixture isolates the accepted branch:
- R1 winner: B
- R1 learning accepted
- Repair Policy advanced
- R2 automatically compiled
- R2 winner: B
- R2 learning accepted
- round cap reached at configured test cap 2
- final `WINNER.mid` + `WINNER.wav` emitted

The synthetic-WAV fixture is not an acoustic-quality claim; it validates auto-loop state/control flow.

## v4.9 learning regression PASS
The existing file-based v4.9 Judge -> Learn -> R2 regression remains PASS:
- objective winner B
- margin 0.1018
- policy generation 0 -> 1
- stale R1 replay rejected

## v4.8 default regression PASS
`policy=None` still preserves v4.8 behavior:
- D 34.314
- A 72.747
- B 76.773
- C 73.207
- structural recommendation B

## Strings regressions PASS
- v4.7 Phrase Long-Line Torch/NumPy parity
- v4.6 Continuous Transition Torch/NumPy parity
- v4.5 Continuous Gesture contract
- v4.4 Ensemble Bow/Phrase contract
- v4.3 Constraint contract
- v4.2 Physical contract
- v4.1 4x4 String Voice contract
- v3.9 Preference Auto Comp contract
- v3.0 Torch/NumPy performance-control parity
- ORT no-Torch: 12000 x 34

## Renderer-service protocol PASS
One current v5.0 source tree, real TCP mock service:
- v4.5 Gesture: 12000 x 34
- v4.4 Ensemble timing: 12000 x 34
- v4.2 Physical String Voice: 12000 x 34
- v4.1 encoded String Voice: 12000 x 34

## Native PASS
Clean VST-independent CMake build completed to 100%.

Native PASS includes:
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
- v3.9 -> v2.7 native regression smokes
- SonicraftInProcessEngineSmoke: 9600 frames / 34 channels
- Promotion Guard + intentional tamper rejection

## Realtime-core non-regression
The following v5.0 files are SHA-256 byte-identical to packaged v4.9:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v5.0 therefore adds orchestration and Shadow-service transport around the validated realtime core.

## Integrity
- project state remains schema v13
- highest explicit ParamID base remains 740
- no new MIDI CC family
- no new ParamID family
- UIDESC XML parses
- installer/prebuilt includes:
  - shadow_render_auto_v50.py
  - compile_musicxml_strings_v50.py
  - auto_loop_strings_v50.py
  - COMPILE_MUSICXML_STRINGS_v50.bat
  - AUTO_LOOP_STRINGS_v50.bat

## Honest boundary
- The trained acoustic weights are not present in this Linux validation environment.
- TCP orchestration/chunking is validated with Renderer Service mock backend, not promoted acoustic weights.
- The accepted two-round WINNER smoke uses controlled synthetic WAV generation to validate loop logic, not sound quality.
- Real trained-model A/B/C/D listening remains a release gate.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v5.0 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
