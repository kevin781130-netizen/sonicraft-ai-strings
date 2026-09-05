# SONICRAFT v4.8 Validation — Phrase Performance Critic & Auto-Repair

Validated 2026-09-02 in the available Linux environment.

## v4.8 PASS
- six-dimension structural critic:
  - Bow Reserve
  - Transition
  - Vibrato
  - Dynamics Arc
  - Gesture Spikes
  - Ensemble Alignment
- deterministic A/B/C repair fanout
- D remains untouched original
- A Conservative / B Balanced / C Expressive are distinct strategies
- B can introduce one safe re-bow split only when bow reserve remains critical
- `.critic.json`
- `.judge_queue.json`
- structural recommendation is explicitly NOT final audio authority
- existing Audio Judge is retained as the final sonic winner step
- no new MIDI CC / ParamID family
- project state remains v13

## Concrete critic regression
A deliberately poisoned 4-note phrase scored:
- D Original: 34.314
- A Conservative: 72.747
- B Balanced: 76.773
- C Expressive: 73.207
- structural recommendation: B

This verifies that repair fanout is materially different and can improve the engineering/performability score.

## Compiler PASS
The v4.8 MusicXML compiler emits:
- D Original MIDI
- A Conservative MIDI
- B Balanced MIDI
- C Expressive MIDI
- score / constraints / ensemble / gesture / transition / phrase sidecars
- critic sidecar
- A/B/C/D Judge Queue

All four test MIDIs parse as:
- format 1
- PPQ 960
- 5 tracks
- v4.8-retagged track metadata

## v4.7 -> v4.1 regressions PASS
- Phrase Long-Line Graph / runtime / compiler / Torch-NumPy parity
- Continuous Transition Graph / pitch path / legacy v4.5 gate / parity
- Continuous Gesture / Physical / Ensemble / 4x4 String Voice regressions
- ORT no-Torch path: 12000 x 34
- Torch / NumPy performance-control parity

## v4.1 -> v4.8 release regressions PASS
Historical release contracts still verify their old runtime/compiler entrypoints while accepting the forward public version.

## Native PASS
Full VST-independent CMake build completed to 100%.

Native executables PASS:
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

Promotion Guard:
- PASS
- tamper rejection: renderer_binding_failed

## Renderer boundary
v4.8 does not modify renderer/runtime audio code. The following files are byte-identical to the validated v4.7 release:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

Therefore v4.8 changes score-domain critic/repair generation, not realtime renderer behavior.

## Integrity
- UIDESC XML parses.
- explicit numeric ParamID bases: no collisions.
- highest explicit ParamID base: 740.
- project state: v13.
- installer/prebuilt includes:
  - string_performance_critic_v48.py
  - compile_musicxml_strings_v48.py
  - COMPILE_MUSICXML_STRINGS_v48.bat

## Honest boundary
- The v4.8 structural critic does not listen to audio.
- Its 0–100 scores are engineering diagnostics, not perceptual/MOS scores.
- Structural recommendation cannot auto-commit the final winner.
- No new acoustic training data, transition recordings, string recordings or preference model is added.
- Final sonic ranking still requires rendering A/B/C/D and using the existing Audio Judge.
- Steinberg VST3 SDK and target Windows/macOS DAW toolchains are unavailable here.
- Rebuilt v4.8 VST3, Steinberg Validator, real Cubase host validation and real Studio One host validation are NOT claimed.
