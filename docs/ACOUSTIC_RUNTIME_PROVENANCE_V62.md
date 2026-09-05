# SONICRAFT v6.2 — Acoustic Runtime Provenance / Model Environment Binding

v6.2 extends the v6.1 project checkpoint without changing the musical decision stack.

## What is bound

`input_state.acoustic_runtime` contains a path-independent `identity` and `binding_sha256` covering:

- renderer implementation source hashes and combined renderer build hash;
- `release_model_manifest.json` hash and re-hashed actual declared weight bytes;
- ONNX `export_manifest.json` and renderer/decoder hashes when present;
- requested and selected backend (`torch`, `ort`, `mock`, or unresolved);
- Torch / CUDA / cuDNN determinism and device-capability observations when Torch is selected;
- ONNX Runtime version/build/device/provider observations when ORT is selected;
- NVIDIA driver/GPU observations when `nvidia-smi` is available;
- OS, architecture, Python runtime and numerical environment variables;
- sample rate, chunk duration, overlap and local-context render settings.

Display-only paths and executable locations stay under `forensics` and are excluded from Checkpoint identity.

## Why actual model bytes are re-hashed

A manifest hash alone only proves which manifest was present. v6.2 also hashes each declared model file and records expected SHA, actual SHA and match state, so replacing a weight while keeping an old manifest changes the binding and is visible.

## Verification semantics

`verify` reports two independent readiness concepts:

- `compile_replay_ready`: Score / Compiler / Evidence inputs are valid for deterministic compiler replay.
- `acoustic_replay_context_ready`: the compile inputs are valid **and** the currently observed acoustic environment matches the checkpoint binding.

A render-configuration change such as 48 kHz -> 44.1 kHz does not falsify compiler determinism. It produces a structured acoustic provenance difference such as `render_config.sample_rate`.

## Interoperability envelope

`PERFORMANCE_CHECKPOINT_V62.bat provenance CHECKPOINT.json` exports an unsigned local in-toto Statement with the SLSA provenance predicate URI. This is intentionally an interoperability/evidence envelope. It is not signed, is not a SLSA-level certification, and does not claim a trusted remote builder.

The implementation uses the SLSA / in-toto data model as a contract rather than adding a heavy provenance server or database runtime dependency.

CycloneDX ML-BOM concepts were used to ensure the model environment is treated as first-class inventory (model artifacts, runtime/framework configuration and dependencies), but v6.2 does not require a CycloneDX runtime library or emit a complete commercial ML-BOM by default.

## Runtime integrations

The implementation directly consumes already-present runtime APIs when available:

- ONNX Runtime provider/build/device introspection;
- PyTorch CUDA capability and determinism/runtime introspection;
- optional `nvidia-smi` driver/device observation.

No MLflow, DVC, model registry, daemon, database, or telemetry service is required.

## Explicit limits

v6.2 does **not** claim:

- bit-identical Audio Replay across GPU/runtime/model changes;
- a rebuilt v6.2 VST3 binary;
- Steinberg Validator pass;
- real Cubase validation;
- real Studio One validation;
- signed commercial installer validation.

It guarantees that the checkpoint records enough local execution provenance to identify material model/runtime/configuration drift that the implementation can observe.

### Existing renderer-process caveat

The v6.2 binding is process-local/runtime-local provenance captured by the Auto-Loop invocation. A separately started older renderer service on the same port is not cryptographically remotely attested by the current v5.0 service protocol. That does not affect compiler replay; for release QA, start the renderer from the v6.2 toolchain or use a dedicated clean service instance before acoustic comparison.
