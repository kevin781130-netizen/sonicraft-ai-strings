# SONICRAFT v2.3 — Native Production Pass

v2.3 does not change the v2.0 acoustic renderer/decoder. It turns the v2.2 platform work into three independent product boundaries.

## 1. Standalone boundary

`SonicraftAIStringsStandalone` is a dependency-free C++20 localhost render host. It speaks the same `SAIR/SAOR` protocol as the VST, can request stereo or Master+11-feed audio, and writes a WAV without requiring the VST3 SDK. `CMakeLists.txt` now supports `-DSONICRAFT_BUILD_VST3=OFF`, allowing standalone-only builds on machines that do not have Steinberg's SDK.

This is intentionally an offline/headless production boundary, not a claim of a finished realtime GUI instrument. A future GUI/audio-device shell can sit on this executable/service boundary without coupling the product to VST3.

## 2. Native runtime promotion

A small runtime is not promoted on file size alone. v2.3 requires all of the following:

- <=160 MiB staged runtime bundle;
- no Torch/TorchVision/TorchAudio/DAC runtime framework leak;
- per-file SHA-256 binding and post-audit artifact rehash;
- renderer + decoder ORT artifacts;
- Torch↔ORT numerical parity evidence;
- >=5-listener / >=60-trial runtime transparency ABX;
- production-target runtime benchmark with p95 real-time factor at or below the declared threshold;
- the existing Schema-7 acoustic promotion.

The production default remains Torch until those real trained-artifact gates pass.

## 3. Embedded ORT staging

`stage_embedded_ort_runtime_v23.py` is an offline staging tool. It downloads nothing and copies only an already-prepared CPython embeddable runtime, NumPy, ONNX Runtime, SONICRAFT runtime Python modules and promoted ORT models. This gives Windows a practical path to a self-contained no-PyTorch bundle while a pure C++ ORT service remains a later optimization.
