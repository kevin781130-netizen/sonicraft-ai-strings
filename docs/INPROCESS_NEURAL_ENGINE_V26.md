# SONICRAFT v2.6 — In-Process Neural Engine

v2.6 leaves the acoustically promoted 3,887,433-parameter neural core unchanged. It removes the localhost/Python renderer service as an architectural requirement by adding a C++ inference graph: timeline events -> deterministic polyphony -> 33-d controls + quartet/phrase context -> few-step flow -> decoder -> 11-feed / 34-channel scoring stage.

The native ONNX Runtime adapter uses the official C++ Session API. ORT-format and ONNX-format models share the same inference API; reduced ORT-format builds remain the deployment target.

## Fail-closed promotion

The in-process path is not automatically production-selected. Formal promotion requires all of:

- pure-native Windows bundle; no Python, PyTorch, `renderer_service.py`, or service executable;
- <= existing native footprint policy;
- six-scenario control/tensor parity: Manual, Assist, Polyphony, Q4/Phrase, Retake, Multi-Out;
- authored MIDI authority parity at <=1e-6;
- renderer/decoder/stage numerical parity;
- existing >=5-listener / >=60-trial runtime ABX transparency;
- v2.3 native runtime promotion;
- v2.5 ultra-low-latency promotion;
- SHA-256-bound renderer, decoder and ONNX Runtime artifacts.

Until these pass with production checkpoints on Windows, `HybridRendererV26` falls back to the localhost production service. `SONICRAFT_INPROCESS_UNSAFE_DEV=1` exists only for engineering experiments and is never a release promotion path.

## Current verified engineering boundary

The cross-platform C++ smoke executes six independent voices through 2-step flow, decoder and 34-channel stage in one process with no socket or Python. This proves the architecture is service-independent; it does not claim acoustic parity with production checkpoints.
