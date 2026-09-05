# SONICRAFT AI Strings Q4 v1.7 — Open-Source Frontier Exit Pass

## Objective
Exhaust high-leverage permissive generic work without growing the consumer footprint, then reserve new capacity for string/ensemble behavior that generic audio generation does not solve.

## 1. Few-step generation without a second shipping network
v1.7 adapts the MIT Shortcut Models training pattern to the existing string latent-flow renderer. The same network is conditioned on flow time `t` and desired jump size `h`. Small jumps keep a normal flow-matching anchor; larger dyadic jumps bootstrap from two EMA half-jumps. The EMA is training-only.

Release metadata can declare `sampling_family=shortcut`, supported powers-of-two step counts, and a recommended step count. The runtime then uses the recommended count for shortcut checkpoints while legacy rectified-flow checkpoints keep their old step behavior.

MeanFlow is pinned as a one-step benchmark/reference, not added as another runtime or training dependency. A dedicated MeanFlow/JVP implementation is only justified if it beats the simpler Shortcut route on the same string data.

## 2. Parameter compression without reducing compute depth
`frontier_shared_dit` retains six computational blocks but shares the AdaLN modulation matrix and fuses the four 4-D physical expert states once rather than through four separate d-model-wide MLPs.

- v1.6 frontier: 3,823,216 parameters
- v1.7 shared frontier: 2,601,136 parameters (-32.0%)
- v1.7 tied challenger: 1,119,856 parameters (-70.7% vs v1.6)

The tied challenger recurrently applies one attention/MLP block six times. It is deliberately not promoted by size alone: held-out transition metrics and string ABX must win first.

With the existing width-16 VAE64 decoder (1,281,137 parameters), theoretical raw FP16 weights are ~7.40 MiB for the shared candidate and ~4.58 MiB for the tied challenger. Framework/runtime bytes are excluded.

## 3. Strict MIDI Authority bug fix
v1.6 overloaded `vibrato_known`: it represented both user CC3 availability and availability of measured real-performance vibrato physics. Runtime therefore risked masking a written CC3 value simply because no depth/rate/jitter teacher labels existed.

v1.7 separates:
- `vibrato_known`: written/user CC3 availability and authority.
- `vibrato_physics_known`: measured depth/rate/onset/jitter teacher-label availability.

The runtime writes the first as known and the second as unknown. This adds zero parameters and restores the intended authority contract.

## 4. SONICRAFT frontier: zero-weight quartet hidden physics
The v1.6 zero-weight re-bow coordinator is extended with deterministic voice-role/density-aware vibrato-bloom staggering. Manual mode remains identity. Assist/Auto may alter only hidden priors; written pitch, note gates/timing, velocity, articulation and explicit CC lanes are never rewritten.

This logic is SONICRAFT-owned code and adds no neural parameters.

## 5. DAW incremental rendering
The renderer already renders long phrases as 10-second audio-domain tiles. v1.7 adds a persistent tile cache keyed by model fingerprint, tile-local controls, sample geometry, inference settings, part and absolute tile position. Editing one phrase segment can therefore reuse unaffected tiles instead of invalidating the complete phrase render.

This is a real workflow optimization with zero model parameters.

## 6. Framework escape hatch remains active
The ONNX/ORT bridge now exports `flow_h` and separate vibrato-physics validity. Schema-4 release metadata carries sampler capability. ONNX Runtime reduced-operator and modular CUDA-provider work remains a deployment migration: PyTorch stays the validated fallback until trained checkpoint parity, ABX, latency, VRAM and binary-size gates all pass.

## Frontier line
After this pass, generic open-source methods still provide useful benchmarks, but a new dependency is not accepted unless it beats the current baseline on at least one hard axis: string realism, score/control fidelity, parameter bytes, framework bytes, latency, VRAM, or DAW edit-to-preview time.
