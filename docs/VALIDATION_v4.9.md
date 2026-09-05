# SONICRAFT v4.9 Validation — Audio Judge Repair Iteration

Validated 2026-09-02 in the available Linux environment.

## v4.9 closed-loop PASS
- local bounded Repair Policy Memory
- five explainable policy multipliers:
  - smoothing
  - bow_relief
  - transition
  - ensemble_tightness
  - expressive_apex
- low-margin gate
- safety gate
- overall-score gate
- stale policy generation/hash rejection
- candidate-specific MIDI-to-Judge event reconstruction
- A/B/C/D comparable render loading
- same sample-rate requirement
- <=50 ms duration mismatch requirement
- accepted Audio Judge winner updates policy
- accepted learning regenerates next round
- max automatic round = 6
- personal Judge Memory remains separate from Repair Policy
- no new MIDI CC / ParamID family
- project state remains v13

## End-to-end synthetic render regression PASS
A real file-based R1 pipeline was exercised:
1. Compile a MusicXML phrase to v4.9 A/B/C/D.
2. Render four synthetic stereo WAVs to the expected filenames.
3. Parse each candidate's own MIDI into Judge events.
4. Run objective Audio Judge on each actual WAV.
5. Winner = B.
6. Winner margin = 0.1018.
7. Safety / overall gates passed.
8. Policy generation advanced 0 -> 1.
9. Policy values moved a small bounded step toward Balanced:
   - smoothing 1.016379035
   - bow_relief 1.015469088
   - transition 1.016379035
   - ensemble_tightness 1.016379035
   - expressive_apex 0.989080643
10. R2 A/B/C/D and a new R2 Judge Queue were generated.
11. Replaying the old R1 render after policy generation advanced was rejected as `stale_policy`.

## v4.8 backward regression PASS
The default policy=None path preserves the original v4.8 critic behavior exactly in regression:
- D Original = 34.314
- A Conservative = 72.747
- B Balanced = 76.773
- C Expressive = 73.207
- structural recommendation = B

This confirms v4.9 policy support did not silently change v4.8 default repair behavior.

## v4.7 -> v4.1 regressions PASS
- Phrase Long-Line graph/runtime/compiler/Torch-NumPy parity
- Continuous Transition graph/runtime/legacy-v4.5 gate/parity
- Continuous Gesture contract
- Ensemble Bow & Phrase contract
- Constraint / Transition contract
- Physical Performance contract
- 4x4 String Voice contract
- historical release contracts v4.1 -> v4.9
- Torch / NumPy performance-control parity
- ORT no-Torch: 12000 x 34

## Native PASS
Clean VST-independent CMake configure/build completed to 100%.

Native executables PASS:
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
- SonicraftTempoSampleMapSmokeV37
- SonicraftInProcessEngineSmoke: 9600 frames / 34 channels

## Renderer service protocol PASS
Current v4.9 tree, one mock renderer service:
- v4.5 Gesture service protocol PASS
- v4.4 Ensemble timing service protocol PASS
- v4.2 Physical service protocol PASS
- v4.1 String Voice service protocol PASS

## Promotion Guard PASS
- promotion binding PASS
- intentional renderer tamper rejected with `renderer_binding_failed`

## Realtime-core non-regression
The following v4.9 files are byte-identical to the packaged v4.8 release:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

v4.9 therefore changes score-domain repair orchestration and local policy learning, not the realtime acoustic renderer.

## Integrity
- UIDESC XML parses.
- explicit numeric ParamID bases have no collisions.
- highest explicit ParamID base remains 740.
- v4.9 adds no realtime control family.
- project state remains v13.
- installer/prebuilt includes:
  - string_repair_policy_v49.py
  - audio_io_v49.py
  - midi_judge_adapter_v49.py
  - compile_musicxml_strings_v49.py
  - iterate_strings_v49.py
  - COMPILE_MUSICXML_STRINGS_v49.bat
  - ITERATE_STRINGS_v49.bat

## Honest boundary
- v4.9 does not autonomously click or render Cubase / Studio One in this environment.
- Four real rendered WAVs are required for actual Audio Judge learning.
- Objective Audio Judge remains an engineering/adherence diagnostic, not human perceptual truth.
- Repair Policy learns only bounded strategy multipliers; it does not retrain the acoustic model.
- No audio, MIDI, score text, identity or cloud data is stored in Repair Policy.
- No new acoustic training data or weights were added.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v4.9 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
