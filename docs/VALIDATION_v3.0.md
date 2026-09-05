# SONICRAFT AI Strings Q4 v3.0 — Validation

Validation date: 2026-09-01  
Version: `3.0.0-host-intelligence-bridge`

## Passed in this work tree

### Python/runtime
- `python -m py_compile runtime/*.py` — PASS.
- `runtime/smoke_ort_backend_v22.py` — PASS, `12000 x 34` output.
- `runtime/smoke_performance_commander_v28.py` — PASS.
- `runtime/smoke_performance_compiler_v29.py` — PASS (backward regression).
- `runtime/smoke_project_bridge_v30.py` — PASS.
  - schema-2 manifest and stable note IDs;
  - tick-0 Q4 Multi host-command snapshot;
  - region patch touches no musical/non-command MIDI data;
  - unrelated authored CC74 remains byte-semantically unchanged;
  - identical input/region/seed produces byte-identical output;
  - command state is restored at region end;
  - an authored SONICRAFT command exactly at the end boundary survives and wins after restore.
- `runtime/smoke_host_command_contract_v30.py` — PASS.
  - Python command map == C++ header CC map;
  - all CC102–119 constants are mapped in VST3 controller source;
  - Q4 Multi/Authority defaults are fail-safe.
- `runtime/smoke_torch_ort_control_parity_v30.py` — PASS.
  - Torch and NumPy control builders match field-by-field through dynamics, vibrato, pitch bend, articulation, transition, attack, phrase/context and v3 Retake/Looseness behavior.
- Mock renderer service + `runtime/smoke_multiout_v22.py` — PASS, `12000 x 34` output.
- `resource/SONICRAFT_AI_Strings_Q4.uidesc` XML parse — PASS.

### Native C++ (VST3-independent)
Clean CMake build configured with:

```text
-DSONICRAFT_BUILD_VST3=OFF
-DSONICRAFT_BUILD_PRODUCT_SHELL=OFF
-DSONICRAFT_BUILD_ORT_INPROCESS_PROBE=OFF
```

Full build — PASS.

Smokes:
- `SonicraftHostCommandLaneSmokeV30` — PASS, contiguous CC102–119 native contract.
- `SonicraftPerformanceCommanderSmokeV28` — PASS.
- `SonicraftParityRngSmokeV27` — PASS.
- `SonicraftInProcessEngineSmoke` — PASS: 6 voices, 12 neural calls, 9,600 frames, 34 channels.
- `SonicraftInProcessPromotionGuardSmoke <temp-dir>` — PASS including tamper rejection.

## v3.0 functional contract validated

- Ordinary MIDI compiles to explicit Q4 MIDI and a schema-2 performance manifest.
- Compiled MIDI carries a host-command snapshot, including **Q4 Multi**, so channel 1–4 routing no longer relies on a manual plug-in layout change.
- SONICRAFT global performance intelligence is representable in standard MIDI CC102–119.
- Region-scoped Retake/Director commands can be changed without rewriting notes, articulation keyswitches or conventional authored CC lanes.
- Region commands restore the pre-region state at the end boundary and respect later authored command automation.
- Retake seed transport is deterministic; the bridge records both requested command values and the effective value after MIDI 7-bit quantization.
- Torch/CUDA and NumPy/ORT performance-control paths now share the v3 behavior contract.
- Runtime/native stage remains Master + 16 stereo aux feeds = 34 interleaved channels.
- No model weights, acoustic architecture or training data were changed by v3.0.

## Not claimed / still requires target-platform validation

- The Steinberg VST3 SDK is not present in this environment. `src/controller.cpp` contains the CC102–119 mapping and source-contract checks pass, but the **VST3 binary was not rebuilt or run through Steinberg Validator here**.
- The Windows Product Shell source was updated only at source/label level; no Windows SDK/toolchain was available for a v3.0 binary build.
- Bundled historical Windows `.exe` files predate this v3.0 source pass and **must not be represented as validated v3.0 binaries**.
- AU/AAX/ARA/direct Cubase or Studio One selection APIs are not implemented by v3.0. The Project Bridge is MIDI-region based.
- Acoustic-quality promotion remains fail-closed and still requires real production weights / rights-cleared data / ABX evidence.
