# v1.7 Frontier Exit

- Added Shared-AdaLN and weight-tied AdaLN-DiT challengers with legacy defaults preserved.
- Added joint physical-expert fusion to remove four duplicated d-model projection MLPs.
- Added interval/step-size conditioning with one learned d-vector.
- Added Shortcut-style one/few-step training using one shipping network; EMA stays training-only.
- Added shortcut checkpoint metadata and runtime recommended-step selection.
- Fixed CC3 authority by separating user vibrato validity from measured vibrato-physics validity.
- Extended zero-weight Q4 coordination to hidden vibrato-bloom staggering.
- Added persistent deterministic tile cache for incremental DAW edits.
- Updated ONNX export bridge for `flow_h` and physical-vibrato validity.
- Added schema-4 sampler metadata and validation.
- Added exact MIT locks for Shortcut Models and MeanFlow.
- Updated installer/prebuilt staging to include the tile cache module.
