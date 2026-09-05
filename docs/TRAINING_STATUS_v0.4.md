# Training status — v0.4

## What is trained by the public-data bootstrap
- Strings-specialized DAC decoder: timbre, bow/noise texture and reconstruction quality.
- MIDI-conditioned renderer bootstrap: pitch, onset, dynamics where source labels are defensible, articulation on isolated material, instrument/player identity.

## What is deliberately *not* faked
- CC3 vibrato amount on sources without a measured/declared vibrato control.
- CC11 expression curves where only rendered amplitude is present.
- Portamento/legato transition labels on isolated notes.
- A whole scale recording mislabeled as one sustained MIDI note.

Those controls stay masked until a genuinely aligned source is available. This is intentional: a smaller amount of truthful supervision is preferred over a larger amount of false labels.

## Release-quality gate
A checkpoint may be technically trainable from public sources but must not be marketed as "recording-indistinguishable" until it passes:
1. owned/explicitly licensed Q4 legato + vibrato + portamento fine-tuning;
2. held-out professional-player tests;
3. blind ABX against real quartet recordings;
4. source-provenance and license audit.
