# SONICRAFT v5.1 Validation — Selective Phrase Local Repair

Validated 2026-09-03 in the available Linux environment.

## v5.1 selective search PASS
- Critic severity + dimension weighting
- source-note -> phrase mapping
- latent bow / transition / gesture / ensemble risk
- low-weight A/B/C repair-location hints
- simultaneous cross-section problem-window merge
- coverage fallback
- max-window fallback
- unknown-location fallback
- long-local-window preflight fallback

Synthetic localization regression:
- damaged phrase: ticks 0..2880
- clean phrase: ticks 6000..7920
- selected coverage: 0.364
- only damaged phrase selected
- forcing coverage limit to 0.20 correctly returns `problem_coverage_too_large`

## Local Shadow render PASS
Actual TCP mock Renderer Service regression:
- full compiled MIDI event history sent to the local request
- selected core: 3..5 seconds
- local request includes pre/post context
- local core compared against same slice of full render
- compared frames: 16000
- maximum absolute sample error: 0.0

This verifies that pre-window controls / active-note state are reconstructed consistently.

## Selective MIDI merge PASS
- D Original remains base
- conductor/meta track remains D
- accepted window channel events come from A/B/C winner
- pre-window compiler CC/keyswitch can be replaced
- end-boundary note-off / Gesture close can be replaced
- a back-to-back next phrase beginning on the exact end tick remains D
- events after selected window remain D

## Selective accepted branch PASS
A deterministic local-Judge fixture exercises orchestration independently from the already-validated Audio Judge:
- one localized problem window
- local winner B
- local margin 0.600
- selective MIDI merge produced
- final merged full render produced through actual mock Shadow Renderer
- final artifact exists
- test cost including final full render = 0.757 of one v5.0 four-full-render round

The fixture only controls the local ranking so the accepted selective orchestration branch is deterministic.
Actual Audio Judge behavior is separately covered by v4.9/v5.0 regressions.

## Low-confidence local -> full fallback PASS
Actual TCP mock Renderer / real Audio Judge path:
- localized phrase found
- local A/B/C/D margin below threshold
- fallback reason = `local_low_margin_W1`
- whole-song A/B/C/D fallback executed
- whole-song confidence remained insufficient
- final status = `review_required`
- REVIEW_BEST MIDI/WAV emitted

## v5.0 regressions PASS
- compiled MIDI -> Shadow event reconstruction
- real TCP mock Shadow render
- >45 s chunk/crossfade: 2 requests, 404000 frames @ 8 kHz
- full auto-loop low-confidence stop
- accepted R1 -> R2 orchestration
- Shadow auto-loop source/release contracts

## v4.9 -> v4.1 regressions PASS
- Repair Policy memory / stale gate
- end-to-end Judge -> learn -> R2
- Performance Critic A/B/C/D
- Phrase Long-Line Torch/NumPy parity
- Continuous Transition Torch/NumPy parity
- Physical Torch/NumPy parity
- String Voice / Ensemble / Constraint source contracts
- Torch/NumPy performance-control parity
- ORT no-Torch 12000 x 34
- historical release/source contracts remain forward compatible

## Native PASS
Clean external VST-independent CMake configure/build completed.

Native executables PASS:
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
- SonicraftInProcessEngineSmoke: 9600 frames / 34 channels

Promotion Guard:
- PASS
- intentional renderer tamper rejected with `renderer_binding_failed`

## Realtime-core non-regression
The following v5.1 files are byte-identical to the packaged v5.0 release:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v5.1 therefore changes search/orchestration/MIDI merge only, not the realtime acoustic renderer.

## Integrity
- UIDESC XML parses.
- explicit numeric ParamID bases have no collisions.
- highest explicit ParamID base remains 740.
- project state remains v13.
- no new MIDI CC or realtime ParamID family.
- installer/prebuilt includes:
  - selective_phrase_search_v51.py
  - shadow_render_selective_v51.py
  - selective_midi_merge_v51.py
  - compile_musicxml_strings_v51.py
  - auto_loop_strings_v51.py
  - COMPILE_MUSICXML_STRINGS_v51.bat
  - AUTO_LOOP_STRINGS_v51.bat

## Honest boundary
- Compute savings are workload-dependent. Diffuse/ambiguous problems intentionally fall back to full v5.0-style rendering.
- Local Judge optimization is not a claim that localized audio always captures every global musical preference.
- Final master is rendered from merged MIDI; local WAVs are not spliced into the master.
- No new acoustic training data or weights were added.
- The trained production acoustic weights are not available in this Linux validation environment.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v5.1 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
