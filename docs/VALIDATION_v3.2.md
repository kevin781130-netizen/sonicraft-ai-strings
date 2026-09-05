# SONICRAFT AI Strings Q4 — Validation v3.2

Version: `3.2.0-live-retake-carousel`
Date: 2026-09-01

## Passed in this environment
- `runtime/smoke_retake_carousel_contract_v32.py` — parameter/UI/state/source contract.
- `SonicraftRetakeCarouselSmokeV32` — deterministic seed bank, cycle-wrap advancement, freeze, manual select, scope safety.
- `SonicraftHostCycleScopeSmokeV31` — v3.1 locator boundary behavior retained.
- `SonicraftHostCommandLaneSmokeV30` — CC102–119 contract retained.
- `runtime/smoke_host_command_contract_v30.py` — Python/C++/VST command contract retained.
- `runtime/smoke_performance_compiler_v29.py` — DAW-native Q4 compiler retained.
- `runtime/smoke_project_bridge_v30.py` — permanent region bridge retained.
- `runtime/smoke_performance_commander_v28.py` — performance contract retained.
- `runtime/smoke_torch_ort_control_parity_v30.py` — Torch/NumPy control parity retained.
- UIDESC XML parses successfully.
- VST-independent CMake native build succeeds with no compiler warnings in this pass.
- `SonicraftInProcessEngineSmoke` — 6 voices / 12 neural calls / 9600 frames / 34 channels.
- `SonicraftInProcessPromotionGuardSmoke` — valid promotion lock accepted and tampered renderer rejected.
- Mock renderer IPC — standard render PASS and 12000 × 34 multi-output PASS.
- ORT no-Torch wiring — 12000 × 34 PASS.

## Important source fix
The v3.1 package contained two consecutive declarations of `scopeBoundaryIndex` in `src/processor.cpp`. This is a C++ compile error in the real VST3 processor translation unit but was invisible to the earlier VST-independent build because that target does not compile `processor.cpp`. v3.2 removes the duplicate and the v3.2 source contract asserts that it cannot reappear.

## Not claimed as passed
- Steinberg VST3 SDK is not installed in this environment, therefore the actual v3.2 VST3 binary was not rebuilt here.
- Steinberg Validator was not run here.
- Windows/macOS host QA was not run here.
- Bundled historical `.exe` files are not validated v3.2 binaries.
- Acoustic/training/model-weight promotion is unchanged and remains separately fail-closed.
