# SONICRAFT AI Strings Q4 v1.6 — Frontier Entry / MIT Exhaust Pass

## Prime directive

Absorb solved permissive engineering until the remaining work is genuinely string-performance-specific. Every imported idea must either improve quality/control or reduce bytes/latency/VRAM. Development references stay off the customer machine.

**Hard optimization target:** strongest usable string renderer at the minimum shipping footprint.

## 1. The largest remaining lever was the latent representation

v1.5 still inherited a `1024 ch @ ~25 Hz` DAC-facing renderer geometry. v1.6 adds a new continuous strings codec challenger built around the public MIT SoundReactor/Oobleck geometry:

- 48 kHz waveform,
- 1600x temporal reduction,
- 64 continuous latent channels,
- 30 latent frames/second,
- VAE mean/log-variance bottleneck,
- Oobleck-style dilated residual encoder/decoder blocks.

SONICRAFT does **not** copy or ship SoundReactor weights. The public SoundReactor checkpoints are not assumed to be suitable for studio strings; rights-cleared string recordings must train the SONICRAFT codec.

The scalar latent state per second changes from `1024*25 = 25,600` to `64*30 = 1,920`, a 13.33x reduction at the renderer/codec boundary.

### Compact decoder variants

`training/models/string_vae64.py` narrows the public architecture for a strings-only challenger. The encoder is training-only. Only the decoder is required for the commercial model pack.

Measured architecture sizes:

| base width | full VAE params | decoder params | decoder raw FP16 |
|---:|---:|---:|---:|
| 16 | 2,546,017 | 1,281,137 | ~2.44 MiB |
| 20 | 3,907,609 | 1,963,981 | ~3.75 MiB |
| 24 | 5,559,249 | 2,791,849 | ~5.33 MiB |

`width=24` is the initial balanced training target. `width=16` is the minimum-footprint challenger. Neither is promoted until blind codec ABX passes.

## 2. Strong codec supervision stays training-only

v1.6 adds a local multi-resolution STFT discriminator and feature-matching path inspired by MIT EnCodec / Stable-Audio-Tools practice. It gives the decoder stronger pressure on bow transients, harmonics and texture without adding a single customer-side discriminator parameter.

Codec objective can combine:

- seven-resolution STFT reconstruction,
- small waveform anchor,
- VAE KL,
- spectral adversarial loss,
- feature matching.

The discriminator, encoder, pitch analyzers and source repositories are all development/training assets only.

## 3. Renderer shrinks with the codec instead of fighting it

New presets:

- `frontier_dit`: `64 latent ch -> d_model 192, 6 blocks, 8 heads, MLP 2x, SDPA`.
- `micro_dit`: `64 latent ch -> d_model 160, 6 blocks, 8 heads, MLP 2x, SDPA`.

Measured renderer parameters:

- v1.5 `nano_dit` on 1024-ch latent: 9,597,552.
- v1.6 `frontier_dit` on 64-ch latent: 3,823,216.
- reduction: 60.2% before quantization.

A width-16 VAE decoder + frontier renderer is ~9.74 MiB of raw FP16 parameters combined. This is a storage arithmetic result, not an acoustic-quality claim.

## 4. Native PyTorch SDPA instead of another runtime framework

The new frontier DiT uses `torch.nn.functional.scaled_dot_product_attention`. On supported CUDA builds PyTorch can select fused Flash/memory-efficient kernels automatically. This avoids carrying xFormers, Triton-only FLA kernels or another attention runtime just to optimize sequences that are only ~300 frames for a ten-second 30 Hz latent tile.

v1.5 DiT checkpoints remain compatible because missing `attention_impl` defaults to the old `nn.MultiheadAttention` topology.

## 5. Codec geometry is now first-class metadata

The old runtime hard-coded `1024` latent channels and `25 Hz`. v1.6 removes that assumption.

Renderer checkpoints carry:

- `latent_ch`,
- `latent_hz`,
- `codec_kind`,
- `codec_sample_rate`.

The Shadow Renderer derives noise tensor shape from the loaded model. It can decode either the old DAC44 route or the new `strings_vae64` decoder route. Schema-3 release manifests declare codec geometry and fail closed if the required decoder role is absent.

This also fixes distillation/reflow scripts so students inherit the teacher's latent geometry rather than silently returning to 1024 channels.

## 6. Newly pinned MIT references

| source | pinned commit | what is extracted |
|---|---|---|
| SoundReactor VAE | `7d5543aa367c3542d01ba32a10805ba76f57b660` | 48k/64-d/1600x continuous VAE + streaming architecture |
| EnCodec | `0e2d0aed29362c8e8f52494baf3e6f99056b214f` | training-only spectral discriminator / feature matching reference |
| KVAE-Audio | `5ed41033232d7a648c7c27c557315df3f9cf1aac` | 2026 48k/64-d full-band quality benchmark |
| BigVGAN | `7d2b454564a6c7d014227f635b7423881f14bdac` | discriminator + anti-aliased periodic activation benchmark |

All checkpoints, example audio and heavyweight assets are excluded by the source lock.

## 7. Sources reviewed but intentionally not imported into runtime

- KVAE-Audio: highly relevant 48 kHz / 64-d benchmark, but its published full model is far larger than the SONICRAFT footprint target. Benchmark architecture only.
- BigVGAN: excellent vocoder/discriminator prior art; full generator and custom CUDA path are unnecessary baggage for a compact continuous VAE. Training/reference only.
- SNAC: MIT, but discrete multi-scale codes are less direct for the current continuous rectified-flow latent objective.
- Mimi: very low-rate streaming design is useful prior art, but its 24 kHz speech-oriented operating point is not the intended full-band studio-string target.
- Flash Linear Attention: MIT and useful at long sequence lengths, but 30 Hz latent tiles are short enough that adding a Triton stack is a poor bytes/maintenance trade.
- AudioDec / FlowDec / Music2Latent / ViolinDiff: excluded from the commercial MIT lane by non-commercial or incompatible terms previously documented.

## 8. Promotion gates

### VAE64 -> release codec

Must beat/tie the incumbent on rights-cleared strings for:

1. blind reconstruction ABX/MUSHRA,
2. bow-noise and attack preservation,
3. vibrato/portamento pitch microstructure,
4. long sustain stability and noise floor,
5. decoder bytes,
6. decode latency/VRAM.

Test width 24 first. If it passes, test 20 and 16 in descending size until quality breaks. The smallest passing width wins.

### frontier_dit -> release renderer

Must pass same-data comparisons for held-out flow/transition metrics, exact MIDI authority, blind render quality, model bytes, latency and peak VRAM. `micro_dit` is evaluated only after `frontier_dit` establishes the 64-d path.

### Reflow -> release schedule

Four-step inference must remain blind-equivalent/preferred before two-step is attempted.

## Where the actual frontier begins after v1.6

The remaining advantage is no longer a generic codec, generic DiT, generic F0 tracker or generic sampler. The next work should be SONICRAFT-specific:

**Strict MIDI Authority + continuous bow/vibrato/transition physics + technique experts + editable Cubase controls + phrase-level neural rendering + quartet interaction + cache-aware DAW scheduling + commercial-safe training provenance.**

That combination is the part worth inventing rather than copying.

## Framework-footprint escape hatch: ONNX Runtime reduced CUDA build

The remaining capacity bottleneck is no longer the SONICRAFT model itself; a generic PyTorch + CUDA Python runtime can outweigh the ~10 MiB candidate core by orders of magnitude. v1.6 therefore adds a **development-only ORT migration bridge**:

1. `training/scripts/export_frontier_onnx.py` exports the exact trained frontier renderer plus VAE64 decoder.
2. `scripts/EXPORT_ORT_FRONTIER.bat` converts ONNX -> ORT format and emits `required_operators_and_types.config`.
3. `scripts/BUILD_REDUCED_ORT_CUDA.bat` clones the pinned MIT ONNX Runtime source on demand and builds only SONICRAFT-required operators, with CUDA as a separable plugin EP.

This path is **not promoted by source-code existence**. The PyTorch runtime remains the verified reference until the same checkpoint passes numerical parity, blind ABX, latency, VRAM, crash/reload and installed-binary-size gates. The purpose of the bridge is to make the eventual runtime-size cut a build decision instead of another architecture rewrite.

## Frontier entry: zero-weight Q4 interaction

`runtime/quartet_interaction.py` is the first SONICRAFT-specific frontier component in this pass. It derives simultaneous-entry, ensemble-density and support-role context across the four written parts, then modifies only the hidden `bow_change_prob` prior in Assist/Auto. It adds **zero model parameters** and Manual is intentionally bit-identical. Score pitch, note gates/timing, velocity, articulation and explicit user automation remain authoritative.
