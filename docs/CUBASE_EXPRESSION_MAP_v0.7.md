# Cubase Expression Map workflow — v0.7

## Native articulation discovery

The VST3 controller implements Steinberg `IKeyswitchController` and reports the same 12 articulation switches used by the engine. A compatible host can query these keyswitch descriptions instead of relying on a separate hard-coded articulation list.

The plugin reports articulation-selection keys as note-on keyswitches:

| Note | MIDI | Articulation |
|---|---:|---|
| C0 | 24 | Sustain |
| C#0 | 25 | Legato |
| D0 | 26 | Portamento |
| D#0 | 27 | Expressive Long |
| E0 | 28 | Marcato |
| F0 | 29 | Staccato |
| F#0 | 30 | Spiccato |
| G0 | 31 | Tremolo |
| G#0 | 32 | Pizzicato |
| A0 | 33 | Trill |
| A#0 | 34 | Harmonic |
| B0 | 35 | Flautando |

## Keep speed as a second Expression Map dimension

Do **not** create separate `Legato Slow`, `Legato Normal`, `Legato Fast`, `Portamento Slow` ... patches. That would turn 12 useful articulations into a large redundant bank.

Use a second Direction-style modifier group for optional **CC20 AI Speed Profile**:

| Modifier | CC20 |
|---|---:|
| Auto Tempo | 0 |
| Slow | 42 |
| Normal | 84 |
| Fast | 127 |

This allows combinations such as `Legato + Slow`, `Portamento + Fast`, `Sustain + Slow Vibrato tendency`, while the articulation remains a single independent keyswitch.

## What the speed modifier means

For Legato, Portamento and Bow-change, CC20 selects a performance-speed region. The CUDA renderer then converts the learned beat-domain duration to the current song tempo. Therefore `Legato + Slow` at 58 BPM is not the same number of milliseconds as `Legato + Slow` at 92 BPM.

For Vibrato, CC20 changes only the rate tendency. Vibrato cycles remain free-running and are not synchronized to beats. **CC3 remains the depth control.**

## Recommended working mode

- Use Expression Map articulation slots for C0–B0.
- Use the speed group only where a musical phrase needs an explicit Slow/Normal/Fast intent; leave it on Auto Tempo otherwise.
- Draw CC1 for bow/dynamic character, CC3 for vibrato depth and CC11 for phrase expression.
- Keep pitch-bend/notes editable. AUTO/HQ rendering must follow the written MIDI rather than replacing it.

A CSV recipe is included under `cubase/`; it is documentation, not a claim that every Cubase version accepts the same proprietary `.expressionmap` file format.
