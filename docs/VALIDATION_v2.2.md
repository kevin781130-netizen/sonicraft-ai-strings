# Validation — v2.2 Platform Kill Gap

## Mechanically validated in the source environment

- 24-channel mock Shadow Renderer IPC: 12,000 frames × 24 channels.
- Legacy stereo Shadow Renderer IPC remains valid.
- Pure NumPy 33-control construction and 24-channel stage output.
- Fake-session ORT end-to-end wiring without importing PyTorch.
- Runtime/service imports with Torch actively blocked.
- Synthetic eleven-IR directional room-profile build.
- Footprint report hashes all staged artifacts.
- Native-runtime promotion synthetic PASS and negative tests for >160 MiB and post-report artifact replacement.
- Shadow client standalone C++17 compile.
- v2.2 source smoke.

## Requires production Windows/artifact validation before promotion

- Full VST3 build and twelve-bus activation in Cubase.
- Real promoted checkpoint ONNX/ORT numerical comparison.
- Measured Windows reduced-runtime installed bytes.
- Runtime transparency ABX on the actual ORT build.
- GPU/CPU latency, VRAM/RAM and dropout/underrun testing.

No acoustic superiority or <=160 MiB production installer claim is made before these gates pass.
