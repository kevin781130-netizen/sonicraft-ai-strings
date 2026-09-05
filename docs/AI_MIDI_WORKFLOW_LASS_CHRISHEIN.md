# AI MIDI workflow: familiar like LASS 3 / Chris Hein, but generative under the hood

## Product rule
The user edits normal MIDI. The AI is not allowed to rewrite pitch, onset, duration, or selected articulation unless a user explicitly enables an automatic assist mode.

## Two layouts, one shared backend
1. **Single Section** (default): one VST instance behaves like a conventional orchestral master patch. Choose Violin I, Violin II, Viola, or Cello. Incoming MIDI is routed to that section regardless of channel. This is the closest workflow to LASS/Chris Hein.
2. **Q4 Multi**: one compact instance uses MIDI CH1-4 for Vln I / Vln II / Viola / Cello.

The eventual AI renderer service must be shared between instances so four Single Section instances do not load four copies of the neural model.

## Articulation surface
C0-B0 remains the 12-articulation bank:
Sustain, Legato, Portamento, Expressive Long, Marcato, Staccato, Spiccato, Tremolo, Pizzicato, Trill, Harmonic, Flautando.

The UI exposes one articulation selector, key switching, host automation, and future Cubase Expression Map generation. It does not expose numbered round robins or duplicate vibrato patches.

## Fixed conventional CC map
- CC1 = Dynamics / bow energy / timbre (not just gain)
- CC3 = Vibrato target
- CC11 = Expression / phrase trim
- CC7 = Output volume
- CC10 = Pan
- CC64 = Hold
- CC68 = Legato override
- CC91 = Room send
- Pitch Bend = expressive pitch/slide request

## Three compact performance controls
- **Transition Speed**: controls the target shape/duration of legato and portamento transitions.
- **Short Tightness**: controls short-note body/release, replacing numbered short patches.
- **Attack Character**: soft <-> firm AI note-head/attack target.

These are VST parameters first. They can later be MIDI-learned without stealing standard CC numbers.

## AI modes
- **Manual**: articulation + CCs are authoritative. AI only supplies invisible micro-variation.
- **Assist** (recommended): AI can infer bow direction, rebow, transition micro-shape, vibrato onset/rate, microtiming, microintonation, and round-robin-like variation. It may not change written notes.
- **Auto**: optional higher-level articulation suggestions/selection. Never the default for professional editing.

## Look Ahead evolution
Like LASS-style look-ahead in intent, but the AI version uses future MIDI to render the next phrase before playback reaches it. During live input it falls back to the low-latency preview path. During DAW playback it pre-renders/caches phrase audio and crossfades to HQ output.

## Hard MIDI Lock
Every HQ render job carries a symbolic fingerprint of note pitch/onset/duration/articulation. Output that drifts beyond tolerance must be rejected or re-rendered. AI realism is never allowed to become composition drift.

## v0.6 tempo-aware AI evolution
Cubase Expression Maps may select the existing 12 articulations exactly as before. A second, optional direction control can send CC20 speed profiles (Auto/Slow/Normal/Fast). This is deliberately separate from the articulation bank so the patch does not explode into `Legato Slow`, `Legato Fast`, `Portamento Slow`, etc.

The renderer combines articulation + host BPM + note duration + interval + speed profile to calculate a physically plausible transition window. Tempo changes inside the Cubase Tempo Track are part of the rendering context.

CC3 is kept familiar but becomes more realistic: the user asks for vibrato depth while AI models onset, rate and irregularity. The four active anchors are Light/Natural/Deep/Intense, with Straight at zero.

## v0.7: native keyswitch discovery + learned speed semantics
The controller now implements VST3 `IKeyswitchController`, so the 12 C0–B0 articulations are reported by the instrument itself. In Cubase, the articulation dimension can therefore be discovered from the VST3 instead of being maintained twice.

Slow/Normal/Fast is now interpreted as a **performance distribution request** rather than a fixed millisecond preset. Rights-cleared real transitions calibrate the beat-domain timing distribution; current host BPM turns that learned musical duration into milliseconds. The optional CC20 speed modifier remains independent of the 12 articulation switches.

The standalone Vibrato and transition experts are also embedded as the exact submodules used by the HQ renderer. Their supervised checkpoints now seed the HQ model directly instead of being side models with no runtime connection.
