# v1.6 Frontier Entry

- Added 48 kHz / 1600x / 64-d continuous strings VAE challenger.
- Added training-only multi-resolution STFT adversarial + feature-matching codec supervision.
- Added 64-d `frontier_dit` and `micro_dit` presets.
- Added zero-third-party PyTorch SDPA attention path while retaining v1.5 MHA compatibility.
- Removed hard-coded 1024-ch / 25 Hz assumptions from Shadow Renderer latent allocation.
- Added generic DAC44 / strings-VAE64 decoder selection and codec metadata.
- Generalized renderer training, distillation and Reflow to teacher/dataset latent geometry.
- Added schema-3 compact model-pack manifest with decoder-role validation.
- Pinned SoundReactor VAE, EnCodec, KVAE-Audio and BigVGAN MIT source snapshots for development-only reference.
- Added v1.6 smoke/compatibility/integrity tests.

### Frontier/runtime closure
- Added zero-weight quartet interaction coordinator for Assist/Auto hidden bow coordination.
- Made installed Runtime self-contained (`flow_sampler`, interaction coordinator, model definitions).
- Removed mandatory Descript DAC dependency from the preferred VAE64 runtime path; legacy DAC is lazy-only.
- Added ONNX Runtime MIT reduced-op/CUDA-plugin migration bridge so framework size can be attacked after acoustic checkpoints stabilize.
