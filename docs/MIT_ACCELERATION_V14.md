# SONICRAFT v1.4 — MIT Acceleration Pass 1

Goal: stop re-inventing solved infrastructure, import permissive code with exact attribution, and reserve proprietary effort for string-performance realism.

## Adopt now

1. **VIOLET (MIT code)** — use its proven direction as the architecture benchmark: aligned MIDI/technique/dynamics conditioning, AdaLN DiT, rectified flow, long-audio overlap rendering. **Do not import its dataset or pretrained checkpoints** because the repository explicitly says third-party assets retain separate terms and the dataset license is still pending.
2. **torchcrepe (MIT)** — make this the optional high-resolution offline F0/periodicity analyzer. This directly improves supervision for CC3 depth/rate, portamento shape and transition confidence without increasing VST runtime size.
3. **Oobleck (MIT)** — codec benchmark only. Replace Descript DAC only if measured ABX quality/size/latency wins after strings-only fine-tuning.
4. **SSSSM-DDSP (MIT)** — borrow semi-supervised parameter-estimation curriculum ideas for real audio where full labels are scarce. Keep out of runtime.

## Explicitly not imported

- VIOLET checkpoints / CSV-TD / subjective audio / linked commercial sample assets.
- Any repository whose code is permissive but model weights or dataset provenance is not separately verified.
- FlowDec core (CC-BY-NC majority), AudioDec core (non-commercial terms), NC datasets.

## Architecture decision

A new `AdaptiveFlowDiT` is added as a compact AdaLN-Zero flow backbone. It can be A/B trained against the existing generic TransformerEncoder. Promotion to release core requires:

- lower held-out flow + transition losses,
- equal or better MIDI-lock tests,
- equal/better blind realism,
- no material runtime/VRAM regression.

This means we steal solved architecture *legally*, but do not accept a regression merely because a paper is newer.
