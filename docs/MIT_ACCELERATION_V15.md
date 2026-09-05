# SONICRAFT AI Strings Q4 v1.5 — MIT Acceleration Pass 2

## Prime directive

Do not re-invent solved infrastructure. Absorb mature permissive source patterns first, keep all third-party datasets/checkpoints/model weights outside the commercial core, and spend proprietary engineering only where public systems still do not complete the full DAW string-performance chain.

**Optimization target:** maximum musical capability and renderer quality at the minimum shipping footprint.

## What changed in this pass

### 1. AdaptiveFlowDiT is no longer an isolated experiment

`training/models/adaptive_flow_dit.py` is now wired through `BalladFlowRenderer` and the normal checkpoint config. The legacy Transformer route remains the default and keeps strict state-dict compatibility; AdaLN-Zero DiT is a challenger that must win measured gates before promotion.

New presets:

- `compact_dit`: architecture-quality challenger.
- `nano_dit`: capacity challenger, 9,597,552 parameters versus 15,944,560 in legacy `compact` (39.8% fewer parameters).
- `hq_dit`: larger teacher challenger.

Parameter count alone is not a quality claim. `nano_dit` is promoted only if it also wins or ties held-out flow/transition losses, strict MIDI lock, blind ABX, VRAM and latency.

### 2. VIOLET-style long-phrase rendering without latent seams

The Shadow Renderer can now split long phrases into independent 10-second tiles with overlap and crossfade after decoding in the **audio domain**. This preserves a small fixed model context and avoids forcing a larger backbone merely to cover long musical phrases.

Runtime cost added: code only. No additional model weights.

### 3. MIDI-authority classifier-free guidance

`runtime/flow_sampler.py` adds batched CFG that keeps score-defining controls authoritative while allowing the learned performance layer to be guided more strongly. Pitch, note gate/onset, velocity, note progress, phrase position, interval context and articulation remain present in the base branch. Expressive controls can be dropped in the base branch.

Default CFG scale remains `1.0` until listening tests prove a higher value improves realism without note or timing drift.

### 4. Reflow / few-step distillation

`training/reflow_distill_renderer.py` trains a student on teacher-generated straight noise-to-endpoint pairs and optionally anchors it to real latent targets. The objective is to reduce the number of runtime ODE evaluations rather than add another model.

Initial target: retain blind quality at 4 steps. Only then test 2 steps.

Runtime parameter increase from the technique: **zero**.

### 5. Pitch-label challenger: TorchFCPE

`training/scripts/analyze_with_fcpe.py` adds an optional training-only FCPE path. TorchCREPE remains the incumbent. FCPE is promoted only if string-specific pitch/vibrato/portamento labels are equal or better for less analysis time/install cost.

No pitch model is bundled with the VST runtime.

### 6. Native-runtime route: ACE-Step C++/GGML as engineering reference

The MIT source lock now includes the ACE-Step VST3/C++ branch only as a development reference for:

- portable GGML CPU/CUDA/Metal/Vulkan execution,
- native Oobleck-VAE implementation and tiling,
- batched CFG,
- GGUF conversion/quantization patterns,
- VST3/native deployment structure.

We do **not** import ACE-Step checkpoints or downloaded GGUF/model weights. The goal is to port only proven runtime techniques to the SONICRAFT renderer after numerical/AB tests, not to inherit a multi-gigabyte music-generation stack.

## Exact pinned MIT source snapshots

| ID | Commit | Role |
|---|---|---|
| VIOLET | `cf0975a752a7ee3cc6e11bb573f9e47c64a0ef97` | AdaLN/RF/conditioning/long-render reference |
| TorchCREPE | `19e2ec3d494c0797a5ff2a11408ec5838fba6681` | incumbent offline F0/periodicity labeler |
| TorchFCPE | `6a149c1afb1c7e7821b71869dfb31ad50c95b516` | fast offline F0 challenger |
| Oobleck | `566a8b4e923e1f3c9d8903a3276758fb2376bcc5` | codec challenger |
| SSSSM-DDSP | `9068d9489808300d2b06bad3f1ab47c1aa40aee3` | semi-supervised parameter-supervision reference |
| rectified-flow | `14b4925ad90abdadaca1f7b5caba5555b84e810a` | reflow/few-step/sampler reference |
| ACE-Step VST3 | `b04bf8aec9be3bdd220050a0cc1c68d045b3b798` | compact native-runtime engineering reference |

The source harvester records actual checked-out commits and refuses imports without a captured license file. It excludes checkpoints, GGUF/model binaries and common audio/model-weight formats.

## Shipping-footprint policy

The consumer package does not need any of the source snapshots above. They are fetched only on development/training machines.

The release footprint hierarchy remains:

1. VST3 + lightweight manager/runtime glue.
2. One chosen compact renderer checkpoint.
3. One chosen decoder/codec checkpoint.
4. Optional model pack downloaded separately when appropriate.

Do not ship two competing backbones, two F0 analyzers, or third-party research repos merely because they were benchmarked during development.

## Promotion gates

### `nano_dit` -> release backbone

Must pass all:

- held-out flow loss <= incumbent,
- transition realism >= incumbent,
- strict MIDI/note-count/pitch/timing lock,
- blind ABX >= incumbent,
- lower model bytes and VRAM,
- equal or lower render latency at the selected step count.

### Reflow -> release sampler schedule

- 4-step render must be blind-indistinguishable or preferable versus the normal teacher schedule on sustained notes, legato chains, portamento, vibrato onset and short articulations.
- MIDI-lock must remain exact.
- 2-step mode is tested only after 4-step passes.

### Oobleck/native codec -> release codec

Promote only if string-only fine-tune beats the incumbent decoder on:

- blind audio quality,
- transient and bow-noise preservation,
- long-sustain stability,
- checkpoint bytes,
- decode latency and peak VRAM.

### Native GGML backend -> release runtime

- numerical output/conditioning parity against the PyTorch reference,
- deterministic request equivalence,
- no DAW audio-thread inference or allocation regressions,
- materially smaller dependency/install footprint.

## Where the no-man's-land begins

After the above mature blocks are absorbed, the remaining core is not “build another generic audio Transformer.” The proprietary frontier is the combined system:

**Strict MIDI Authority + Cubase Expression workflow + tempo-aware string transition physics + continuous learned CC3 vibrato + per-technique experts + compact neural phrase renderer + asynchronous Shadow Render + quartet interaction + commercial-safe provenance.**

That combined DAW product chain is where new engineering effort should concentrate. Everything upstream that a mature permissive project already solved stays a benchmark or is absorbed through a clean license boundary.
