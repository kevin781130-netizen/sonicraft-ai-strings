# SONICRAFT AI Strings Q4 v7.0 RC2 — Source Validation Record

## Release meaning

`7.0.0-rc2` is a **commercial release-gate layer** over the frozen v6.2 core and v6.4 frontend. It is not a claim that Windows/DAW/model gates have already been executed.

## Executed in this build environment — PASS

- Clean CMake configure/build with `SONICRAFT_BUILD_VST3=OFF`, `SONICRAFT_BUILD_PRODUCT_SHELL=OFF`, `SONICRAFT_BUILD_ORT_INPROCESS_PROBE=OFF`: **PASS / 100%**.
- `SonicraftPerformanceCheckpointSmokeV62`: **PASS**.
- `SonicraftPerformanceCheckpointSmokeV61`: **PASS**.
- `SonicraftEvidenceStoreSmokeV60`: **PASS**.
- `SonicraftStringExpressionSmokeV41`: **PASS**.
- `SonicraftTakeCompSmokeV33`: **PASS**.
- `SonicraftInProcessEngineSmoke`: **PASS**.
- `SonicraftInProcessPromotionGuardSmoke` with its required temporary promotion directory: **PASS**, including tamper rejection.
- Python syntax compilation across runtime/frontend/scripts/installer/tools: **245 / 245 PASS**.
- Release/version contracts v4.1 through v7.0: **23 / 23 PASS**.
- v6.4 frontend smoke: **PASS** (`9` VSTGUI templates, `188` control tags, Editor→MusicXML→v6.2 compiler bridge PASS).
- v7 frontend consumer-packaging smoke: **PASS**.
- v7 pinned-SDK/source gate: **PASS**.
- v7 final-gate destructive smoke: **PASS**:
  - missing evidence cannot approve;
  - stale VST3 host evidence revokes approval;
  - replacing a model manifest after acoustic QA revokes approval;
  - public mode cannot approve without signature evidence.

## Release-process defects closed in v7.0

1. **Moving VST3 SDK dependency removed.** Windows commercial build pins Steinberg VST3 SDK 3.8.0 to commit `9fad9770f2ae8542ab1a548a68c1ad1ac690abe0`.
2. **Validator provenance bound to the build.** The official Validator is built from the same pinned SDK and records its own SHA plus the exact tested VST3 SHA.
3. **No stale host evidence.** Cubase and Studio One reports are bound to the current VST3 SHA, concrete host executable/version, and host executable SHA-256.
4. **No stale acoustic evidence.** RTX/model QA is bound to both the exact VST3 SHA and the exact `release_model_manifest.json` SHA-256.
5. **Frontend actually ships.** `frontend/` is now staged under `App/Frontend`, exposed by Manager, and required by the prebuilt-layout verifier.
6. **BAT recovery path survives installation.** Current compiler/Auto-Loop/Checkpoint BATs detect both source-tree and installed `App/Tools + App/Runtime` layouts and prefer the packaged runtime venv when present.
7. **Approval is fail-closed.** Missing/SKIP/stale evidence cannot create or retain `RC_APPROVED.txt`.
8. **Runtime Python compatibility fixed.** ONNX Runtime 1.29 requires Python ≥3.11, while the pinned Torch 2.8 build supports Python 3.11–3.13 and CUDA 12.8. Runtime bootstrap therefore uses Python 3.11–3.13 and rebuilds an old incompatible venv instead of retaining Python 3.10.

## Intentionally NOT RUN / NOT CLAIMED here

- Windows x64 v7.0 VST3 rebuild.
- Official Steinberg Validator execution against the v7.0 Windows binary.
- Windows ProductShell build.
- Cubase real-host QA.
- Studio One real-host QA.
- Final trained/approved acoustic model pack.
- RTX 5090 acoustic render/checkpoint QA.
- Authenticode signing/verification of the public artifact.
- Bit-identical Audio Replay.

Those items are not source-code TODOs. They are the remaining machine/model evidence gates and are intentionally impossible for `FINAL_GATE_V70` to silently bypass.

## RC2 frontend convergence

The v7.0 RC2 source pass adds the fail-closed `runtime/frontend_layout_gate_v70.py` and integrates it into `RC_SOURCE_GATE_V70`. It statically checks responsive editor constraints, VSTGUI parent/child bounds, text and segmented-control fit, UI/audio-parameter collision guards, Manager DPI/resize behavior, and Product Shell Per-Monitor DPI source contracts. See `FRONTEND_LAYOUT_LOCK_v7.0_RC2.md`. Windows host rendering remains NOT_RUN until real-machine QA.

## RC2 frontend lock validation result

Source-level result after convergence:

- Frontend Layout Gate: **PASS**
- Standalone Editor → MusicXML → existing compiler bridge: **PASS**
- Consumer frontend packaging: **PASS**
- Runtime installer compatibility: **PASS**
- Fail-closed release gate destructive smoke: **PASS**
- Release/version contracts: **23/23 PASS**
- Python source syntax: **388/388 PASS**
- Clean non-VST CMake build: **PASS**
- Native smoke executables: **37/37 PASS** (the PromotionGuard smoke requires its documented temporary model-root argument)

This does not convert any Windows/DAW/acoustic NOT_RUN item into PASS. The detailed frontend constraints are in `FRONTEND_LAYOUT_LOCK_v7.0_RC2.md`, and the machine-readable summary is `../release/FRONTEND_LOCK_VALIDATION_v7.0_RC2.json`.
