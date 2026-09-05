# SONICRAFT AI Strings Q4 v3.1 — Validation

Validation date: 2026-09-01  
Version: `3.1.0-host-native-locator-scope`

## Passed in this work tree

### v3.1 host-native scope

- `runtime/smoke_host_scope_contract_v31.py` — PASS.
  - VST parameter IDs 120–122 are unique and present in processor/controller/UI source.
  - processor requests VST3 cycle music + project time.
  - locator start/end and in-block boundary scheduler are wired.
  - component state schema is v7 and controller accepts v3–v7.
  - MIDI host-command map still ends at CC119; CC120–127 are not repurposed.
- `SonicraftHostCycleScopeSmokeV31` — PASS.
  - range inclusion/exclusion boundaries;
  - Retake forced Off outside a scoped range;
  - Director override only inside the range;
  - deterministic locator boundary sample-offset calculation.
- `resource/SONICRAFT_AI_Strings_Q4.uidesc` — XML parse PASS with Host Scope controls.

### Backward regression

- `python -m py_compile runtime/*.py` — PASS.
- `runtime/smoke_host_command_contract_v30.py` — PASS.
- `runtime/smoke_project_bridge_v30.py` — PASS.
- `runtime/smoke_performance_compiler_v29.py` — PASS.
- `runtime/smoke_performance_commander_v28.py` — PASS.
- `runtime/smoke_torch_ort_control_parity_v30.py` — PASS.
- `runtime/smoke_ort_backend_v22.py` — PASS, `12000 x 34` output.
- Mock renderer service + `runtime/smoke_multiout_v22.py` — PASS, `12000 x 34` output.

### Native C++ (VST3-independent)

Clean CMake configure/build with:

```text
-DSONICRAFT_BUILD_VST3=OFF
-DSONICRAFT_BUILD_PRODUCT_SHELL=OFF
-DSONICRAFT_BUILD_ORT_INPROCESS_PROBE=OFF
```

Full build — PASS.

Smokes:

- `SonicraftHostCycleScopeSmokeV31` — PASS.
- `SonicraftHostCommandLaneSmokeV30` — PASS, CC102–119 contract.
- `SonicraftPerformanceCommanderSmokeV28` — PASS.
- `SonicraftParityRngSmokeV27` — PASS.
- `SonicraftInProcessEngineSmoke` — PASS: 6 voices, 12 neural calls, 9,600 frames, 34 channels.
- `SonicraftInProcessPromotionGuardSmoke` — PASS including tamper rejection.

## v3.1 functional contract validated

- Host Scope is a second regional-control path; it does not replace the persistent v3.0 Project Bridge.
- With valid VST3 project-time and locator/cycle data, a Retake can be constrained to the locator range without rewriting MIDI.
- Scoped Retake becomes Off outside the range while global non-Retake settings remain intact.
- Scoped Director overrides Style/Looseness inside the range and preserves global Director state outside.
- Locator boundaries occurring inside a process block are scheduled into the block event timeline.
- v3.0 Command Lane CC102–119 remains backward compatible.
- MIDI CC120–127 remain untouched.
- v3.1 state schema adds three parameters with backward defaults for older v3.0 sessions.
- No model weights, acoustic architecture, or training data changed.

## Not claimed / target-platform gate

- Steinberg VST3 SDK is not installed in this environment. The VST3 processor/controller source has been updated and source contracts pass, but the **v3.1 VST3 binary has not been rebuilt or run through Steinberg Validator here**.
- Cubase/Studio One host behavior therefore still requires target-machine validation with the rebuilt VST3. The implementation uses standard VST3 ProcessContext cycle/project-time fields rather than private DAW APIs.
- The bundled Windows `.exe` files are historical binaries and are **not validated v3.1 binaries**.
- AU/AAX/ARA are still not implemented by SONICRAFT v3.1.
- Acoustic-quality promotion remains fail-closed pending production weights / rights-cleared training data / ABX evidence.
