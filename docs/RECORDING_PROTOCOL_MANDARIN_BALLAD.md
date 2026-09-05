# Rights-cleared Mandarin Ballad Q4 recording protocol

This session is the critical dataset for reaching the target of being difficult to distinguish from a real recording.

## Players

Minimum authentic ensemble:
- Player A — Violin I
- Player B — Violin II
- Player C — Viola
- Player D — Cello

Keep player identities stable in metadata. Do not synthesize Vln II by simply copying Vln I takes.

## Recording format

- 24-bit / 96 kHz masters
- fixed, documented gain per player/take family
- no limiter, denoiser, aggressive EQ or loudness normalization on masters
- close mic per player; optional stereo room pair with fixed geometry
- room impulse/room-tone capture at beginning/end
- slate take ID verbally or through session metadata

## Core solo capture per player

Recommended 60–90 minutes/player:

### Long tones
- practical instrument range
- pp / mp / mf / f / ff
- no vibrato + natural vibrato
- 3–6 s note duration
- several bow directions/round-robin takes

### Dynamic trajectories
- 4 s and 8 s crescendo
- 4 s and 8 s diminuendo
- pp->mf, mp->f, mf->ff and reverse

### Vibrato
- none
- narrow/natural
- medium
- delayed onset (roughly 0.3–1.2 s depending on phrase)
- varied natural rate rather than mechanically fixed LFO behavior

### Legato transitions — highest priority
- interval classes ±1 through ±12 semitones over practical ranges
- slow and medium connection speeds
- pp / mf / f families
- repeated takes with genuine bow/finger variation
- separate slurred and bow-change transitions where musically valid

### Portamento
Prioritize intervals frequently heard in lyrical pop melodies: 2nd, 3rd, 4th, 5th, 6th and octave. Record restrained and expressive variants; avoid exaggerated gliss as the default.

### Shorts/colors
- marcato
- staccato
- soft spiccato
- tremolo
- pizzicato
- trill
- harmonic
- flautando

## Copyright-clean phrase studies

Record original/non-infringing studies rather than melodies copied from released songs.

Suggested tempo families: 58 / 64 / 72 / 80 BPM.

Per instrument, cover:
- 2–4 bar lyrical melody fragments
- long-note swell into cadence
- delayed-vibrato entrance
- restrained portamento into emotional target note
- repeated-note re-bowing
- inner-voice thirds/sixths
- cello root movement + lyrical counterline

## Quartet ensemble takes

Recommended 30–45 minutes minimum:
- 4-part homophonic pad swells
- melody + three-part support
- contrary-motion phrase
- staggered entrances
- synchronized cadence releases
- pp intimate passage and mf/f chorus lift

Do not quantize the audio. Preserve each player's microtiming, intonation and bow behavior.

## Minimum rights grant before training a release model

The signed agreement should explicitly cover:
- ownership/permission for the master recordings and performer contributions
- commercial machine-learning training
- creation of derivative models, parameters and learned weights
- redistribution and sublicensing of model weights
- commercial generation and distribution of rendered audio outputs
- editing, segmentation, resampling, annotation and augmentation of recordings
- worldwide, perpetual scope appropriate to the intended product
- ability to distribute the model without distributing raw session audio
- consent to synthetic/inferred performance generation from learned characteristics

Have the final agreement reviewed for the governing jurisdiction. Store the signed document path/hash in model provenance before changing the session from `release_blocked` to eligible.
