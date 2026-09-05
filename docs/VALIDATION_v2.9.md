# SONICRAFT AI Strings Q4 v2.9 — Validation

Validation date: 2026-09-01
Version: `2.9.0-daw-native-performance-compiler`

## Passed in this work tree

### Python/runtime
- `python -m py_compile runtime/*.py` — PASS.
- `runtime/smoke_performance_commander_v28.py` — PASS.
- `runtime/smoke_ort_backend_v22.py` — PASS, `12000 x 34` output.
- `runtime/smoke_performance_compiler_v29.py` — PASS.
- Mock renderer service + `runtime/smoke_multiout_v22.py` — PASS, `12000 x 34` output.
- `resource/SONICRAFT_AI_Strings_Q4.uidesc` XML parse — PASS.

### Native C++ (VST3-independent)
Configured from a clean build directory with:

```text
-DSONICRAFT_BUILD_VST3=OFF
-DSONICRAFT_BUILD_PRODUCT_SHELL=OFF
-DSONICRAFT_BUILD_ORT_INPROCESS_PROBE=OFF
```

Full build — PASS.

Smokes:
- `SonicraftPerformanceCommanderSmokeV28` — PASS.
- `SonicraftParityRngSmokeV27` — PASS.
- `SonicraftInProcessEngineSmoke` — PASS: 6 voices, 12 neural calls, 9,600 frames, 34 channels.
- `SonicraftInProcessPromotionGuardSmoke` — PASS including tamper rejection.

## v2.9 functional contract validated
- Smart Divisi produces four explicit Q4 parts while preserving source note pitch/onset/duration.
- DAW-native compiler emits a Type-1 MIDI conductor track + Vln I / Vln II / Viola / Cello tracks.
- Compiler emits editable keyswitch, CC1 and CC3 data and a `.performance.json` sidecar.
- Retake contract supports Off/Timbre/Dynamics/Vibrato/Micro-Pitch/Timing Feel/Bow-Attack/All.
- MIDI Authority Lock prevents Retake micro-pitch mutation when enabled.
- Runtime/native stage contract is Master + 16 stereo aux feeds = 34 interleaved channels.
- Legacy 2-channel and 24-channel renderer/cache responses remain accepted intentionally for backward compatibility.

## Not claimed / still requires target-platform validation
- The Steinberg VST3 SDK is not included in this source archive, so a full VST3 binary build/validator run was not performed in this environment.
- The Win32 Product Shell source was updated to expose all v2.9 performance controls and 16 aux feeds, but it was not compiled here because this environment does not provide the Windows SDK/toolchain.
- AU/AAX/ARA are not implemented or validated by v2.9.
- Acoustic-quality promotion remains fail-closed and still requires real production weights / rights-cleared data / ABX evidence. v2.9 does not claim an acoustic-quality improvement.
