# SONICRAFT v6.2 Changelog

## Added
- Acoustic Runtime Provenance schema 1.
- Path-independent acoustic runtime binding in every v6.2 Checkpoint.
- Actual declared model-weight SHA-256 verification in addition to manifest hashing.
- ONNX export manifest and ORT model hashing.
- Renderer implementation/build fingerprint.
- Torch / CUDA / cuDNN runtime and determinism observations.
- ONNX Runtime build/device/provider observations.
- NVIDIA driver/device observation when available.
- OS / Python / numerical-environment binding.
- Sample-rate / chunk / overlap / local-context render configuration binding.
- Structured acoustic-environment drift reporting.
- Unsigned local in-toto Statement / SLSA provenance-shaped export.
- v6.2 compiler, Auto-Loop and Checkpoint management entrypoints.
- Native v6.2 provenance contract smoke.

## Preserved
- v6.1 deterministic compile replay semantics.
- v6.0 Evidence Store and checkpoint pin retention.
- v5.9 through v4.6 musical decision algorithms.
- project state v13.
- highest explicit ParamID base 740.
- no new MIDI CC family.
- no new acoustic weights or training data in this source package.

## Deliberately not added
- MLflow / DVC / model-registry services.
- provenance database or daemon.
- mandatory new third-party Python dependency.
- bit-identical Audio Replay claim.
