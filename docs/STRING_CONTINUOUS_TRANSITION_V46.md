# SONICRAFT v4.6 Continuous Transition & Legato Path

## Graph link
Two notes are linked only when they share one explicit String Voice lane, are bowed, are close enough in time, and the written/physical plan already indicates Slur, Legato or Portamento intent.

The graph classifies:
- same-string portamento
- cross-string portamento
- same-bow legato shift
- same-bow string crossing
- re-bow legato shift
- re-bow string crossing

It records interval, fingering shift, string crossing, same-bow state, transition duration and continuity.

## Gesture boundary reconciliation
Before MIDI is written, the last v4.5 anchor of note A and the first anchor of note B are reconciled.

Continuous dimensions:
- Dynamics Energy
- Vibrato Depth
- Bow Pressure
- Contact Point
- Bow Speed
- Micro-Pitch drift convergence
- Portamento intent

Same-bow links use a continuous mechanical state. Re-bow links deliberately dip pressure/speed to represent a physical release/re-attack instead of falsely smoothing through the bow change.

## Phrase-window contract
v4.5:
`CC38 ON → note → CC38 OFF`

v4.6 connected phrase:
`CC38 ON → note A → note B → note C → CC38 OFF`

This is the version gate. No new CC is necessary.

## HQ pitch path
Inside a multi-note CC38 window, the runtime uses the actual written note pitches to build a short smoothstep pitch-conditioning trajectory around each connected boundary.

Explicit Portamento uses a longer path; ordinary Legato uses a short transition. MIDI note pitches remain unchanged.

The runtime also:
- removes the redundant second-note hard onset;
- sets `transition_target_ms`;
- raises Legato intent;
- softens transition-speed control;
- carries Vibrato envelope through the boundary;
- avoids resetting Note Progress to hard zero at the transition head.

## Legacy safety
A v4.5 file closes CC38 at every note. Therefore two old v4.5 windows touching at the same sample are not a v4.6 link and do not receive the new pitch path.

## Acoustic honesty
The transition graph provides continuous conditioning to the existing renderer. It does not claim new captured transition samples or a newly-trained phase-continuous acoustic model.
