# v6.2 Open-source Integration Decisions

Goal: fastest commercial convergence with minimum dependency/size growth.

## Adopted directly or as a contract

1. **SLSA Provenance v1 vocabulary** — used for the optional interoperability envelope and resolved-dependency/material semantics.
2. **in-toto Statement v1 shape** — used as the outer attestation envelope. Export remains unsigned/local.
3. **CycloneDX ML-BOM concepts** — used as a design checklist for first-class model/runtime/framework inventory; no CycloneDX package dependency is required.
4. **ONNX Runtime native introspection** — provider, build, device and version information is captured when ORT is selected.
5. **PyTorch native introspection** — CUDA capability, framework/build and determinism settings are captured when Torch is selected.
6. **NVIDIA system probe** — `nvidia-smi` is queried best-effort when available.

## Deliberately deferred

- MLflow: useful experiment/model registry but unnecessarily heavy for checkpoint-local provenance.
- DVC: useful dataset/model versioning but duplicates existing SHA/manifest ownership and adds workflow/runtime surface.
- full CycloneDX generation library: useful for later enterprise/compliance export, not needed for v6.2 runtime correctness.
- new model serialization layer: existing model-pack integrity and ORT manifests already provide the authoritative bytes to bind.

This keeps v6.2 dependency-light while preserving an upgrade path to signed attestations / full ML-BOM export later.
