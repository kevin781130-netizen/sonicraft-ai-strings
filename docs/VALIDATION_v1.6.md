# SONICRAFT AI Strings Q4 v1.6 — Engineering Validation

Date: 2026-08-31

## Passed in this source package

- VAE64 geometry: 48,000 samples -> 30 latent frames at 64 channels -> 48,000 samples.
- VAE64 forward/backward finite output.
- v1.4 legacy Transformer strict state-dict compatibility.
- v1.5 AdaLN-DiT/MHA strict state-dict compatibility.
- v1.6 64-ch `frontier_dit` SDPA forward/backward.
- Rectified-flow sampling + MIDI-authority CFG on 64-ch latent.
- Runtime latent geometry: 10 s -> `(64, 300)` rather than hard-coded `(1024, 250)`.
- Schema-3 `strings_vae64` release-manifest integrity path.
- Third-party source lock uses exact commits and excludes common model/audio assets.

## Measured architecture counts

- v1.5 `nano_dit`: 9,597,552 params.
- v1.6 `frontier_dit`: 3,823,216 params, 60.2% smaller.
- VAE64 width 16 full training model: 2,546,017 params.
- VAE64 width 16 release decoder: 1,281,137 params (~2.44 MiB raw FP16).
- `frontier_dit + width16 decoder`: ~9.74 MiB raw FP16 parameters.

The combined number excludes Python/PyTorch/CUDA/framework binaries and is therefore not an installer-size claim.

## Not claimed yet

No final rights-cleared string codec/render checkpoints are bundled. Consequently this validation does **not** claim that VAE64, `frontier_dit`, `micro_dit`, 4-step Reflow, or future quantized/native exports already win acoustically. Promotion still requires the listening and release gates in `docs/MIT_ACCELERATION_V16.md`.

## Additional frontier/deployment validation

- `runtime/quartet_interaction.py`: Manual mode identity and Assist coincident-entry intervention covered by `training/smoke_v16.py`.
- Self-contained runtime import: PASS after copying only `runtime/` into an isolated temporary directory; no project `training/` tree was available on `sys.path`.
- Shadow Renderer mock localhost IPC after the self-contained-runtime changes: PASS, 48,000 stereo frames returned.
- Runtime installer/prebuilt staging now includes `flow_sampler.py`, `quartet_interaction.py`, and the minimal `Runtime/models/` inference definitions.
- ONNX/ORT migration scripts are syntax/package artifacts only in this source release because no trained v1.6 commercial checkpoint is bundled. They remain non-promoted until checkpoint parity and Windows CUDA binary-size benchmarks are run.
