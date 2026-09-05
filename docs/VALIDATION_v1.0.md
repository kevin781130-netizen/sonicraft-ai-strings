# Validation v1.0

Validated in the artifact environment:

- Python compile of runtime/training modules.
- Binary IPC protocol sizes and round-trip parsing.
- Local mock renderer service request/response.
- Cache hit with a different request id for the same phrase.
- ShadowAudioCache fixed-slot audio mixing.
- C++ ShadowRenderClient compilation with warnings as errors.
- LIVE preview compilation with warnings as errors.
- VSTGUI XML parsing.
- Native x64 Windows Renderer Service launcher is a PE32+ executable.
- Setup payload marker / embedded ZIP integrity.
- ZIP CRC integrity.

Not claimed as validated here:

- MSVC/Steinberg SDK Windows VST3 binary build.
- Cubase host scan/playback on Windows.
- CUDA inference with final rights-cleared production weights.
- Real-recording-indistinguishable ABX result.

Those require the target Windows/CUDA machine and final trained checkpoints. Missing neural weights intentionally fall back to LIVE rather than producing fake HQ audio.
