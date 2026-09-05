# Q4 patch + MIDI controller map (v0.7)

The patch is deliberately smaller than large commercial orchestral libraries. Continuous controllers replace redundant articulation slots whenever the musical dimension should be continuous.

## 12-key articulation bank

| Keyswitch | Articulation | Mandarin-ballad role |
|---|---|---|
| C0 / MIDI 24 | Sustain | default warm arco |
| C#0 / 25 | Legato | primary lyrical line |
| D0 / 26 | Portamento | tasteful expressive connection |
| D#0 / 27 | Expressive Long | swells and held melody notes |
| E0 / 28 | Marcato | controlled accented entrances |
| F0 / 29 | Staccato | normal short note |
| F#0 / 30 | Spiccato | light rhythmic short note |
| G0 / 31 | Tremolo | tension / lift |
| G#0 / 32 | Pizzicato | pop-arrangement punctuation |
| A0 / 33 | Trill | ornament |
| A#0 / 34 | Harmonic | airy color |
| B0 / 35 | Flautando | intimate soft color |

Not separate patches in v0.2:
- Sustain Vibrato -> **Sustain + CC3**
- Dynamic Long/Short -> **CC1 + CC11**
- multiple numbered Short/Spiccato -> AI round-robin/performance variation
- Runs -> MIDI notes remain editable; renderer performs the written notes
- clusters/effects/col legno/ponticello -> postponed until a rights-cleared dataset justifies them

## Conventional controller behavior

- **CC1 Dynamics**: bow energy / spectral intensity / dynamic layer. It must not behave as a simple volume fader.
- **CC3 Vibrato**: continuous vibrato depth/character. 0 = no/near-no vibrato; upper range = stronger vibrato. The AI renderer may delay vibrato onset naturally while respecting the requested amount.
- **CC11 Expression**: phrase-level amplitude/expression trim after the dynamic/timbre decision.
- **CC7 Volume**: channel output trim.
- **CC10 Pan**: channel panorama.
- **CC64 Sustain/Hold**: note hold behavior.
- **CC68 Legato Override**: forces/permits connection behavior where required.
- **CC91 Room**: room/reverb send.
- **Pitch Bend**: expressive pitch/slide input; HQ mode interprets it as a performance cue, not a generic post-resample pitch effect.

VST3 exposes these through `IMidiMapping` so host automation and MIDI hardware behave conventionally.

## Four-part routing

- MIDI CH1 -> Violin I
- MIDI CH2 -> Violin II
- MIDI CH3 -> Viola
- MIDI CH4 -> Cello

Violin I/II share a violin family backbone but use different player identities and micro-performance states.


## LASS / Chris Hein-style AI workflow additions in v0.3

- Default layout: **Single Section** master patch, one orchestral track per Vln I / Vln II / Viola / Cello.
- Optional compact layout: **Q4 Multi**, CH1-4 as before.
- AI Performance Assist: Manual / Assist / Auto.
- AI Look Ahead: predictive phrase renderer; does not require destructive MIDI nudging.
- Transition Speed: continuous legato/portamento timing/shape control.
- Short Tightness: replaces duplicate Short 1/3/5/6-style slots.
- Attack Character: AI note-head/attack control.
- Auto Divisi exists only as an optional helper and defaults off for explicit Q4 writing.
- Standard CC assignments remain unchanged.

## v0.7 CC3 depth anchors + learned tempo-aware performance

CC3 is explicitly a **vibrato depth request** with four active depth anchors plus straight:

- CC3 0: Straight / essentially no vibrato (about 0 cents peak)
- CC3 32: Light (about 12 cents peak)
- CC3 64: Natural (about 28 cents peak)
- CC3 96: Deep (about 48 cents peak)
- CC3 127: Intense (about 72 cents peak)

The AI does not turn these into a rigid LFO. It predicts rate, onset delay and small cycle-to-cycle instability while holding the requested depth. Values between anchors interpolate continuously.

Optional **CC20 AI Speed Profile** exists for Cubase Expression Maps: `0=Auto Tempo`, `42=Slow`, `84=Normal`, `127=Fast`. In v0.7, Slow/Normal/Fast select beat-domain performance regions rather than hard-coded millisecond values. Legato, Portamento and Bow-change are converted from learned beat fractions to the current Cubase tempo at CUDA/shadow render time.

CC20 may also request a Slow/Normal/Fast **vibrato-rate tendency**, but vibrato is never phase-locked to BPM. **CC3 remains the authoritative vibrato depth lane.** CC20 is optional; the conventional CC1/CC3/CC11 workflow is unchanged.

The VST3 controller also exposes all 12 articulation keyswitches through `IKeyswitchController`, so compatible hosts can discover the articulation bank directly. Speed remains a separate modifier and does not multiply the patch list.
