# Real Recording Pipeline v0.8

## Commercial-safe flow

```text
Public / owned real string recordings
        |
        v
Rights + source audit (fail closed)
        |
        +--> hash + provenance
        |
        v
Acoustic analysis @ 100 fps
  F0 / RMS / centroid / flux
        |
        +--> Vibrato physical labels
        |      depth cents
        |      rate Hz
        |      delayed onset ms
        |      cycle irregularity
        |
        +--> conservative bow-change candidates
        |
        v
Aligned intended MIDI/control required for Expert supervision
        |
        +--> Legato transition timing in beats
        +--> Portamento slide timing/extent/curve
        +--> Bow-change timing/strength/continuity
        |
        v
Per-output confidence masks
        |
        v
Vibrato + Performance Experts
        |
        v
HQ renderer -> Compact distillation
```

## Why real audio without alignment is not automatically Expert data
A chamber recording can be excellent for codec/realism learning while being unsafe for direct CC3 or Legato supervision. If we do not know the intended note, articulation and note boundary, the system must not pretend that an F0 wiggle means a specific user control.

## CC3 calibration
The user continues to edit one lane:
- 0: Straight
- ~32: Light
- ~64: Natural
- ~96: Deep
- 127: Intense

The cents at these anchors are **learned from the commercial-safe real corpus**. The mapping is continuous between anchors and may be instrument-specific. Thus violin, viola and cello do not need identical physical vibrato extent to feel like the same CC3 musical intention.

## Tempo behavior
- Vibrato rate remains human/free-running; BPM is weak context only.
- Legato, Portamento and Bow-change transition durations are learned in beat-domain and converted from the current Cubase tempo.
- Expression Map Slow/Normal/Fast expresses intent; CUDA computes the physical duration for the local tempo, interval, register and phrase context.

## Real-recording manifest row examples
Single note:
```json
{"dataset":"good_sounds_cora_2025","audio":"D:/data/vn.wav","instrument":"violin","midi_note":69,"dynamic":"mf"}
```
Aligned phrase:
```json
{"dataset":"custom_owned_session","audio":"D:/session/VlnI_take03.wav","control_npz":"D:/session/VlnI_take03_controls.npz"}
```
Mixed-license/per-file source additionally requires `license` plus `source_url`/`provenance_url` and must pass the v0.8 audit.

## Expert index vs HQ latent index
Real analyzed recordings may train/calibrate Vibrato/Legato/Portamento/Bow-change Experts even before a matching DAC latent package exists. v0.8 deliberately keeps this **Expert index separate from the HQ renderer latent index**. The HQ trainer only receives rows containing `latent`; supervised Expert weights are then loaded into the exact submodules embedded in the HQ renderer. This prevents non-latent real-analysis rows from accidentally entering a renderer batch.
