# v0.7 Performance Experts

## Objective

The largest perceptual gap between a good string library and a convincing live recording is often not the stationary sustain. It is the changing behavior around note connections: attack suppression, bow continuity, pitch trajectory, vibrato onset, rebow transients and the way all of these scale with phrase tempo.

v0.7 therefore treats four behaviors as separate expert problems and lets the HQ flow renderer fuse their residual performance state.

## 1. Vibrato Expert

User authority remains **CC3**. The release-facing anchors are:

| CC3 | Label | Approx. peak depth target |
|---:|---|---:|
| 0 | Straight | 0 cents |
| 32 | Light | 12 cents |
| 64 | Natural | 28 cents |
| 96 | Deep | 48 cents |
| 127 | Intense | 72 cents |

Values between anchors interpolate continuously. These are conditioning anchors, not five sample layers.

The expert predicts natural secondary behavior: rate tendency, delayed onset, cycle-to-cycle jitter and evolution across the note. Optional CC20 can request a Slow / Normal / Fast **rate tendency** without changing CC3 depth. Vibrato is never phase-locked to tempo.

## 2. Legato Expert

Inputs include pitch, interval context, CC1, velocity, note progress, phrase position, current BPM, note duration in beats, speed quantile, transition-speed trim and instrument identity.

Targets include:

- transition duration in **beats**, not fixed milliseconds;
- note overlap ratio;
- attack suppression;
- continuity.

At render time the learned beat-domain target is converted to milliseconds using the current Cubase tempo and constrained by physical minimum/maximum values.

## 3. Portamento Expert

Portamento is not treated as merely “slow legato.” It has its own targets:

- transition duration in beats;
- slide extent;
- pitch-trajectory curve shape;
- arrival softness.

The user's Portamento keyswitch remains authoritative. The AI chooses the detailed performance trajectory inside that instruction.

## 4. Bow-change Expert

Targets:

- rebow / bow-change timing in beats;
- transient strength;
- local brightness change;
- continuity through the change.

This expert is deliberately mask-gated because bow-change labels are easy to hallucinate from audio. If the source does not provide reliable alignment or explicit bow information, it does not supervise this expert.

## Slow / Normal / Fast is learned, not hard-coded

`training/fit_timing_calibration.py` converts rights-cleared real transition durations into beat fractions and estimates distribution quantiles. The intended mapping is:

- **Fast** ≈ 20th percentile
- **Normal** ≈ 50th percentile
- **Slow** ≈ 80th percentile

If there is insufficient trustworthy data, the system falls back to conservative musical priors rather than fabricating supervision. This makes the behavior usable before the proprietary recording session, but the fallback must not be mistaken for final learned performance.

## MIDI authority rule

The experts are not allowed to rewrite the musical content. Pitch targets, note on/off, written timing, articulation selection, CC1, CC3, CC11 and pitch bend remain user/host authority. Experts only render the physically plausible path between those instructions.

## Supervision integrity in v0.7

The independently trained experts are not dead-end side models. Their exact `VibratoControlExpert` and `PerformanceExperts` modules are embedded inside `BalladFlowRenderer`. When a valid expert checkpoint is produced in the current run, HQ training warm-starts those exact submodules, preserves them for a short warm-up, then refines them end-to-end.

Physical labels are dimension-masked. For example, F0 alignment may provide a trustworthy Legato transition duration while providing no trustworthy overlap ratio or attack-suppression measurement. In that case only the timing output receives supervised loss. Unknown dimensions remain masked rather than being filled with plausible-looking constants.
