# v1.5 Source Scout — what was absorbed, challenged, or rejected

The filter is deliberately stricter than “open GitHub repository”: commercial-safe source terms, measurable technical advantage, and no unnecessary shipping dependency.

## Absorbed / benchmarked through the MIT boundary

- VIOLET — direct domain architecture reference: aligned score/technique/dynamics -> AdaLN rectified-flow violin renderer.
- TorchCREPE / TorchFCPE — offline pitch-label competition; never shipping runtime dependencies.
- Oobleck — continuous codec challenger only.
- SSSSM-DDSP — scarce-label semi-supervised supervision reference.
- rectified-flow — reflow/few-step sampler acceleration.
- ACE-Step VST3 / C++ GGML — native deployment, tiling, batched guidance and quantized-runtime engineering reference only.

## Explicitly rejected from the MIT-only vendor path

- ViolinDiff — technically relevant separate pitch-bend + synthesis design, but the project states non-commercial/research-only terms. Do not copy code/checkpoints into a commercial product.
- Music2Latent — attractive low-rate music latent representation, but the library is CC BY-NC 4.0. Do not use it in the commercial core.
- MIDI-DDSP / DDSP — valuable hierarchical performance-control prior art, but Apache-2.0 rather than the current MIT-only vendor lane. Keep as conceptual/benchmark reference unless a separately tracked Apache layer is intentionally enabled.
- auraloss — mature audio loss library but Apache-2.0, so the existing local loss path remains independent in the MIT-only branch.

## Redundant MIT options not automatically added

Generic inference/codec projects are not vendored simply because they are MIT. For example, ONNX Runtime and EnCodec are valid commercial source options, but adding another runtime or codec branch increases engineering surface. They become challengers only if they can beat the selected GGML/DAC path on the measured size/quality/latency gates.

## Frontier rule

A new upstream source is accepted only when it does at least one of these better than the current project:

1. raises string-performance realism or control fidelity,
2. reduces model/runtime bytes,
3. reduces render latency/VRAM,
4. materially improves commercial/provenance safety,
5. eliminates bespoke infrastructure we would otherwise need to maintain.

If it does not win one of those dimensions, it does not enter the tree.
