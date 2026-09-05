# SONICRAFT AI Strings Q4 v1.7 — Engineering Validation

Validated in the supplied engineering environment on 2026-08-31.

## PASS
- v1.4 AdaptiveFlowDiT smoke.
- v1.5 legacy Transformer + AdaLN-DiT forward/backward, sampler, CFG, tile slicing and strict checkpoint compatibility.
- v1.6 VAE64 forward/backward, SDPA frontier, legacy strict-load, schema-3 integrity.
- v1.7 shared/tied frontier forward/backward.
- v1.7 1-step and 2-step interval-conditioned sampling path.
- v1.7 Shortcut bootstrap loss backward pass using one student + training-only EMA.
- CC3 authority / physical-vibrato-validity split contract.
- zero-weight Q4 Manual identity + role-dependent Assist hidden-vibrato behavior.
- persistent tile-cache round trip.
- schema-4 sampler/codec integrity.
- self-contained Runtime import with the Source tree absent.
- localhost mock Shadow Renderer IPC: 48,000 frames / 384,000 payload bytes.
- ONNX bridge Python forward path accepts `flow_h` and `vibrato_physics_known`.

## Parameter counts
- v1.6 frontier renderer: 3,823,216
- v1.7 shared frontier renderer: 2,601,136 (-32.0%)
- v1.7 tied challenger renderer: 1,119,856 (-70.7%)
- width-16 VAE64 consumer decoder: 1,281,137
- shared + decoder theoretical raw FP16: 7.40 MiB
- tied + decoder theoretical raw FP16: 4.58 MiB

These are architecture/footprint results, not acoustic-quality claims. Promotion still requires trained held-out transition metrics and blinded string ABX.

## Not validated in this source-only package
- final commercial v1.7 trained checkpoints;
- real 1-step/2-step string ABX;
- PyTorch-vs-ORT numerical parity on trained checkpoints;
- Windows reduced-ORT CUDA binary size/latency/VRAM;
- final VST3 release binary with commercial model pack.
