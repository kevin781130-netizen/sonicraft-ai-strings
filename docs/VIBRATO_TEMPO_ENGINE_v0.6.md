# v0.6 Vibrato + tempo-aware performance engine

## CC3 remains the only required vibrato lane
CC3 controls requested **depth**, not a fixed LFO rate. Stable anchors are:

| CC3 | Name | target peak pitch deviation |
|---:|---|---:|
| 0 | Straight | 0 cents |
| 32 | Light | ~12 cents |
| 64 | Natural | ~28 cents |
| 96 | Deep | ~48 cents |
| 127 | Intense | ~72 cents |

The values between anchors are continuous. The AI Vibrato Expert predicts rate, delayed onset and micro-jitter from instrument/register/phrase context. Vibrato rate is **not tempo-locked**; tempo is only weak context because real players do not synchronize every vibrato cycle to the click.

## Tempo-aware transitions
The VST reads Cubase/VST3 `ProcessContext::tempo` every block. CUDA/shadow rendering must receive the same tempo map, not only a project-level BPM.

Legato, portamento and bow-change timing is represented in beat fractions first and then converted to milliseconds with physical clamps. This means a transition naturally shortens in a faster song and lengthens in a slower song without becoming physically absurd.

Optional **CC20 AI Speed Profile** is intended for a Cubase Expression Map:
- 0 = Auto Tempo
- 42 = Slow
- 84 = Normal
- 127 = Fast

This does not replace `Transition Speed`; it provides convenient discrete performance anchors. The normal continuous Transition Speed parameter remains a fine trim.

## Data policy
Release vibrato supervision must come only from rights-cleared audio. v0.6 includes a deterministic pitch-trajectory analyzer using torchaudio autocorrelation; it can estimate vibrato depth/rate/jitter from commercial-safe source manifests without training on a restricted reference dataset.

The public Doga Cavdir/MTG vibrato material is technically useful because it contains no/slow/standard/fast vibrato and pitch-trajectory annotations, but the public record does not provide one unambiguous commercial ML + learned-weight redistribution grant for all embedded audio. It therefore remains research-reference-only.

## Four realism experts
1. Vibrato Expert — CC3 -> depth/rate/onset/jitter.
2. Legato/Portamento Transition Expert — note intervals + articulation + project tempo + speed profile.
3. Bow-change Expert — predicts re-bow character and timing from phrase/dynamics/tempo.
4. Base HQ Renderer — integrates experts without changing written notes or timing authority.

## v0.6 two-axis vibrato performance
For realism, vibrato is now explicitly split into two performer dimensions while keeping the DAW simple:
- **CC3 = depth**: Straight / Light / Natural / Deep / Intense, continuously interpolated.
- **CC20 Speed Profile = rate tendency**: Slow / Normal / Fast. It is an optional Expression-Map modifier, not a mandatory automation lane.

The speed profile changes the human rate prior (roughly within 4.0–7.2 Hz depending on player/instrument/register), but never locks vibrato cycles to quarter notes or the click. Song BPM remains a weak phrase-context input only. In contrast, Legato / Portamento / Bow-change transition durations are beat-relative and therefore strongly tempo-aware.

## CUDA render-job tempo authority
The neural path is designed to receive **frame-wise tempo**, not a single project BPM. `training/tempo_timeline.py` represents VST3 musical positions (`projectTimeMusic`, quarter-note units) plus the host-reported tempo points and can generate a per-frame BPM curve for each phrase. Therefore tempo automation/ramps can change transition timing inside a phrase.

For the eventual out-of-process CUDA renderer, every phrase job must carry: beat start/end, sampled tempo points, articulation/speed profile, and the original MIDI note boundaries. A cached Shadow render is invalidated when a newly observed host tempo point changes the phrase's tempo signature. Final/offline rendering remains authoritative because the host supplies the actual ProcessContext while rendering.

The VST3 processor also overrides `getProcessContextRequirements()` to explicitly request host tempo, musical project position and transport state. This matters with modern VST3 hosts because these context fields are optional unless requested.
