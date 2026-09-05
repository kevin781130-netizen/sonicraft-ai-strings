# Mandarin Ballad Q4 — quality-first training plan

## Hard product rule

**If commercial model-training rights AND learned-weight distribution rights are not clear, the source does not enter a release checkpoint.** Free download is not enough.

## Target sound

Intimate-to-lush Mandarin pop-ballad strings rather than symphonic/trailer strings:
- lyrical connected lines
- soft attacks
- slow crescendos/diminuendos
- natural delayed vibrato
- restrained, intentional portamento
- warm inner viola
- singing cello counterline
- low bow noise retained where musically natural
- stable pitch with small human microvariation
- dry/close core that can be placed into a pop mix

## Stage 0 — safe public bootstrap

1. **Descript DAC** provides the high-fidelity 44.1-kHz codec initialization.
2. Fine-tune **decoder only** with Iowa strings as the dominant fidelity/timbre anchor.
3. TinySOL supplements controlled pitch coverage.
4. VSCO 2 CE is legally permissive but is kept out of the HQ acoustic renderer by default; its available string layout is not a matched four-soloist Q4 corpus. It remains an optional articulation/LIVE-preview reference.
5. Generate copyright-clean MIDI control studies for tempo, dynamics, vibrato, articulation and voice-leading coverage.

This can bootstrap a good instrument, but isolated-note public data cannot create recording-indistinguishable legato/phrase behavior by itself.


## Controller-label trust policy

Public bootstrap sources are not allowed to invent labels they do not actually provide:
- **CC1**: Iowa pp/mf/ff labels are trusted as coarse dynamic anchors; custom session supplies continuous cresc/dim curves.
- **CC3**: public isolated-note sources are **not** treated as authoritative continuous-vibrato supervision. The final CC3 response must come from the rights-cleared custom session with no-vibrato, natural-vibrato and delayed-vibrato takes.
- **CC11**: treated as arrangement/phrase expression control; final response is learned from custom phrase captures, not guessed from sample amplitude.
- **Legato/Portamento**: never inferred from isolated sustain samples. Final transition behavior requires explicitly recorded note-to-note transitions.

This prevents the model from learning fake controller semantics from convenient but mislabeled data.

## Stage 1 — mandatory rights-cleared Mandarin-ballad session

The final renderer must be fine-tuned on paired real performance data recorded specifically for the model. This is the most important dataset for the product.

Priority order:
1. real note-to-note legato transitions
2. natural delayed vibrato
3. cresc/dim trajectories
4. tasteful portamento
5. bow-change / re-articulation texture
6. phrase timing
7. four-player interaction
8. coherent close/room microphone perspective

See `RECORDING_PROTOCOL_MANDARIN_BALLAD.md`.

## Stage 2 — model training

### Audio model
- base codec: DAC 44.1 kHz / 16 kbps
- preserve original dynamics; never peak-normalize each training clip independently
- decoder fine-tune priority: rights-cleared professional recordings > Iowa; TinySOL is mainly control/pitch support and VSCO is excluded from HQ acoustic training by default
- output: high-quality SRC to DAW/host sample rate (48 kHz target workflow)

### Performance renderer
Condition on:
- pitch / gate / onset / velocity
- CC1 dynamics
- CC3 vibrato
- CC11 expression
- articulation
- legato flag
- pitch bend
- instrument identity
- player identity

The neural renderer predicts continuous codec latents with rectified flow. It is trained to obey the MIDI exactly while using audio data to learn how humans connect and shape notes.

## Stage 3 — objective release gates

A checkpoint is not called HQ/release until it passes:
- provenance gate: no blocked source
- MIDI lock: pitch/onset/duration drift below project threshold
- reconstruction ABX: codec does not erase bow texture or soft dynamics
- transition ABX: real vs generated legato on held-out players/phrases
- phrase ABX: generated vs real pop-ballad phrase study
- mix test: dry close rendering sits naturally under vocal/piano without sample-like attacks

The final acceptance criterion is listener confusion against held-out real recordings, not merely lower training loss.
