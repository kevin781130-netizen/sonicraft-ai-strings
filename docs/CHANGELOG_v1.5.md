# CHANGELOG — v1.5 MIT Acceleration Pass 2

- Wired `AdaptiveFlowDiT` into the normal `BalladFlowRenderer` training/checkpoint/runtime-compatible configuration path.
- Kept legacy Transformer checkpoints strict-load compatible by retaining the original default backbone topology.
- Added `nano_dit` challenger: 9,597,552 params vs 15,944,560 legacy compact (-39.8%).
- Added compact Euler/Heun rectified-flow sampler with MIDI-authority CFG.
- Added deterministic phrase seeding and inference settings to the renderer fingerprint/cache identity.
- Added fixed-context tiled long rendering (10 s default / 1 s overlap) with audio-domain weighted crossfade.
- Added Reflow distillation path targeting fewer runtime ODE steps with optional real-data anchoring.
- Added TorchFCPE as a training-only F0 challenger to TorchCREPE.
- Expanded the pinned MIT source lock with exact commits for Oobleck, SSSSM-DDSP, TorchFCPE, rectified-flow and ACE-Step VST3/C++ runtime reference.
- Hardened source license capture to accept common MIT license filenames while still refusing imports with no captured license.
- Added one-click v1.5 smoke, Reflow distillation and FCPE analysis scripts.
- Third-party source/checkpoints remain outside the lean shipping runtime by default.
