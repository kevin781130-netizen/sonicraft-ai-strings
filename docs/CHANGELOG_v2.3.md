# Changelog — v2.3 Native Production Pass

- Fixed stale prebuilt `build-info.json` version/channel metadata.
- Made VST3 build optional and added a standalone-only CMake path.
- Added a dependency-free C++20 Standalone Render Host using the existing renderer protocol.
- Validated standalone stereo and 24-channel Master+11-feed WAV output.
- Added rights-confirmed logarithmic sweep generation and eleven-feed room IR recovery/deconvolution.
- Added embedded-Python+ORT offline staging for a self-contained no-PyTorch Windows runtime candidate.
- Added v2.3 footprint verification with deployment-kind checks and per-artifact SHA-256 binding.
- Added production-target renderer RTF benchmark evidence.
- Upgraded native runtime promotion to require footprint + artifact binding + numerical parity + runtime ABX + p95 RTF + existing acoustic promotion.
- Kept the consumer neural core unchanged at 3,887,433 parameters (~7.41 MiB raw FP16).
