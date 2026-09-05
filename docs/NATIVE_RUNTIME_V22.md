# v2.2 Native Runtime Promotion

## Goal

Remove PyTorch from the shipping inference path without changing the promoted sound.

## Candidate path

1. Export the acoustically promoted renderer and VAE64 decoder.
2. Convert them to ORT format and generate the required-operator/type configuration.
3. Build a reduced ONNX Runtime candidate pinned to an exact upstream commit.
4. Stage the runtime binary/wheel and both models.
5. Run `VERIFY_NATIVE_RUNTIME_V22.bat`; every staged artifact is hashed.
6. Render the same held-out anchors with Torch and ORT and run `compare_runtime_audio_v22.py`.
7. Run the runtime-only blind transparency ABX.
8. Combine those reports with the valid acoustic-promotion report through `PROMOTE_NATIVE_RUNTIME_V22.bat`.

The installer accepts `-RuntimeBackend ort -OrtWheel <custom-wheel>` for a reduced candidate. Without `-OrtWheel`, the pinned PyPI ORT wheel is only a developer validation bridge. Product default remains Torch until the promotion report passes.

## Size rule

The default maximum staged native runtime is 160 MiB. This is a gate/target, not a claim that the current source archive has already produced a Windows runtime below that size.
