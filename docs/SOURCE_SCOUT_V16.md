# v1.6 MIT Source Scout — final known-road sweep

## Absorb now

- **SoundReactor VAE (MIT):** strongest fit for the capacity target. Use its 48 kHz, 1600x, 64-d continuous-VAE geometry and Oobleck/streaming engineering as the codec baseline. Do not use upstream weights as SONICRAFT production weights.
- **EnCodec (MIT):** absorb discriminator/feature-matching training patterns only; do not turn the renderer into a discrete-token model.
- **PyTorch SDPA:** use built-in fused attention dispatch instead of shipping another attention framework.
- **ACE-Step C++/GGML (already pinned):** remains the native-runtime/quantization engineering reference after acoustic architecture stabilizes.

## Benchmark, do not ship

- **KVAE-Audio (MIT):** 2026 full-band 48 kHz / 64-d continuous VAE; important quality ceiling, but far too large to inherit as the minimum-footprint core.
- **BigVGAN (MIT):** anti-aliased periodic activation and strong discriminators are useful codec QA/training references; full generator/custom kernel stack is redundant.
- **SNAC (MIT):** excellent discrete codec engineering, but continuous RF integration would add a tokenization detour with no proven string benefit.
- **Mimi:** impressive streaming/low-rate prior art, but 24 kHz speech-first design does not directly satisfy the studio 48 kHz string target.
- **FLA (MIT):** efficient long-sequence kernels are unnecessary at ~300 latent frames/10 s after 30 Hz compression; PyTorch SDPA is the leaner solution.

## Still blocked from MIT-only commercial lane

ViolinDiff, Music2Latent, AudioDec and FlowDec retain the license restrictions documented in earlier scouts. MIDI-DDSP/DDSP/auraloss remain outside the intentionally MIT-only vendor boundary.

## Decision rule

No more repositories enter the consumer path merely because they are impressive. A new source now needs to beat the v1.6 baseline on **string realism, control fidelity, model bytes, runtime bytes, latency or VRAM**. Otherwise it stays a benchmark.

### ONNX Runtime — ACCEPT as framework-footprint escape hatch
- License: MIT.
- Pinned commit: `27e64f961d36fa34b8393fd1743fbc5cf579af16`.
- Why it matters now: ORT format can generate a required-operators configuration for reduced custom builds, and current CUDA support can be built as a separable plugin EP.
- What SONICRAFT takes: export/build path only. Generic prebuilt Python runtime is not automatically the shipping answer; the goal is a model-specific reduced native runtime after parity gates.
