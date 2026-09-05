# Changelog — v2.2 Platform Kill Gap

- Added Master + eleven stereo VST3 auxiliary outputs and 24-channel shadow-render transport.
- Preserved legacy stereo wire/cache behavior when aux outputs are not active.
- Added Torch and NumPy 11-feed stage bundles.
- Added directional room-profile builder from owned/explicitly licensed IRs.
- Added pure-NumPy control construction and stage rendering.
- Added opt-in no-PyTorch ONNX Runtime backend.
- Made `flow_sampler.py` lazily import Torch so no-Torch runtime modules can import cleanly.
- Pinned ONNX Runtime v1.29.0 to exact commit `2e2543fbe9fae542f921d47a72d21d5a4ef0b710`.
- Added reduced CPU/CUDA ORT build entry points.
- Added <=160 MiB native-runtime footprint gate with per-file SHA-256 evidence.
- Added numerical parity and native-runtime promotion gates tied to runtime ABX + existing Acoustic Promotion.
- Hardened promotion to rehash the staged artifacts at promotion time.
- Added installer `-RuntimeBackend ort -OrtWheel <path>` path while keeping Torch default.
- Consumer neural parameters remain unchanged.
