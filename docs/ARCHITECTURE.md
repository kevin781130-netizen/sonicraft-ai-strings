# Q4 architecture v0.2

## Runtime
- MIDI CH1: Violin I
- MIDI CH2: Violin II
- MIDI CH3: Viola
- MIDI CH4: Cello
- LIVE: internal low-latency preview synthesis (no neural model in audio callback)
- AUTO/HQ parameters are reserved for the shadow neural renderer integration.

## Training
### Stage A — Strings Codec
48 kHz mono string audio -> compact latent -> reconstructed audio.
The legacy LIVE/smoke codec has ~4.96M parameters and a 256x temporal reduction (~187.5 latent frames/s at 48 kHz). This is deliberately higher-rate than a music-generation codec to preserve bow attacks and transitions.

### Stage B — MIDI/Performance latent renderer
For aligned phrase data, build 25 Hz control tracks:
- pitch
- note gate
- dynamics
- instrument (Vln/Vla/Vc)
- articulation (reserved)

HQ mode instead targets continuous Descript-DAC latents using a phrase-aware rectified-flow Transformer with CC1/CC3/CC11, onset, legato, pitch bend, articulation and player identity. Compact/HQ capacity is selected only after data-quality gates pass.

### Stage C — quartet interaction (next scaling axis)
Do not make four independent solo renders and merely pan them. Add a shared conductor state and per-player offsets for timing, pitch, vibrato and bow-change. The same Q4 core can then drive a Section Multiplier without training a full large-orchestra model.

## Quality scaling order
1. More rights-cleared professional real recordings.
2. Better codec/adversarial spectral training.
3. Explicit articulation + bow/dynamics annotation.
4. Phrase-aware renderer context.
5. Player/ensemble interaction.
6. Mic/room model.
7. LoRA adapters for orchestra/room/player style.

LoRA is intentionally not step 1.


## HQ acoustic hierarchy

1. Rights-cleared 24/96 real recordings are the target.
2. Iowa is the public clean timbre bootstrap.
3. TinySOL adds controlled pitch coverage.
4. VSCO 2 CE is an optional articulation/LIVE reference only and is excluded from HQ acoustic training by default because the available viola/cello material is section-oriented rather than a matched Q4 soloist corpus.
5. Ambiguous/non-commercial datasets are evaluation/research only.

The architecture intentionally separates **musical control** from **acoustic truth**. A source can be useful for control pretraining without being allowed to define the final timbre.
