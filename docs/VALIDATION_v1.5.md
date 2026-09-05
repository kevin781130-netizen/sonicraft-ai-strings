# SONICRAFT AI Strings Q4 v1.5 — Validation Record

Date: 2026-08-31

## Engineering checks executed

- `training/smoke_v14.py` — PASS
  - legacy v1.4 AdaptiveFlowDiT smoke remains functional.
- `training/smoke_v15.py` — PASS
  - legacy renderer forward/backward,
  - AdaLN-DiT renderer forward/backward,
  - MIDI-authority CFG sampler,
  - tiled control slicing,
  - strict legacy state-dict load compatibility,
  - capacity comparison.
- Shadow Renderer mock service + `runtime/smoke_client.py` — PASS
  - localhost binary protocol,
  - 48,000-frame response,
  - finite/non-zero stereo float32 payload.
- Python compile checks — PASS for all v1.5 touched runtime/training modules.
- MIT source lock — PASS: no floating `HEAD` revisions remain.

## Capacity measurement

Measured model parameters with the shipped Python architecture definitions:

- legacy `compact`: 15,944,560 params.
- `nano_dit`: 9,597,552 params.
- reduction: 39.8%.

Approximate raw weight storage before graph/runtime overhead:

- legacy compact FP16: ~30.4 MiB.
- nano_dit FP16: ~18.3 MiB.
- nano_dit theoretical 4-bit weights: ~4.6 MiB.

The 4-bit number is a storage lower-bound estimate, **not** a validated release artifact. Quantization may require mixed precision for sensitive layers and must pass ABX/MIDI-lock tests.

## What this validation does not claim

No rights-cleared acoustic training corpus or final production checkpoints are bundled in this source package, so this pass does **not** claim that `nano_dit`, Reflow 4-step inference, FCPE, Oobleck, or a future native GGML backend already beat the incumbent acoustically.

Promotion requires the held-out and blind-listening gates in `docs/MIT_ACCELERATION_V15.md`.
