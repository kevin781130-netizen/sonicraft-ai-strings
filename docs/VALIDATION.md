# v0.2 validation — 2026-08-30

## Passed in the artifact runtime

- Python source tree: `python -m compileall -q training` passed.
- Mandarin Ballad Flow Renderer forward pass passed:
  - compact: 15,292,288 parameters; output shape preserved; all finite.
  - HQ: 33,116,672 parameters; output shape preserved; all finite.
- Compact renderer one optimizer/backward step passed on synthetic latent/control tensors.
- Release provenance gate passed on an allowed Iowa/DAC fixture and correctly failed closed on a blocked URMP fixture.
- Isolated-control preparation passed on 24/96 Violin/Viola/Cello AIFF fixtures and preserved pp/mf/ff values rather than per-clip peak-normalizing them.
- Copyright-clean Mandarin-ballad Q4 MIDI generator produced valid 4-part files containing CC1/CC3/CC11 and articulation keyswitch data.
- `src/preview_engine.cpp` compiled cleanly standalone with g++17 warnings enabled.

## Not executed here

- Full Descript-DAC decoder fine-tune was not executed because the artifact runtime does not have the DAC package/model weights installed and has CPU-only PyTorch.
- Full commercial-source training was not executed here; the real datasets are intentionally not bundled into the project archive.
- Full VST3 binary build was not executed because the Steinberg VST3 SDK / Windows Visual Studio toolchain is not installed in this artifact runtime.

Use `scripts/START_TRAIN_MANDARIN_BALLAD_HQ.bat` on the target Windows/CUDA machine after downloading the enabled datasets.

## Important quality boundary

Passing these engineering smoke tests does **not** mean the current bootstrap model is recording-indistinguishable. That quality target requires the rights-cleared real Q4 recording protocol in `RECORDING_PROTOCOL_MANDARIN_BALLAD.md`, followed by held-out real-vs-generated ABX evaluation.
