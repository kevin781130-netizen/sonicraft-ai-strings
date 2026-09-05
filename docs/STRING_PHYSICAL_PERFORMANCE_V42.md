# SONICRAFT v4.2 String Physical Performance Graph

## Purpose
Convert score intent into explainable string-playing decisions before rendering, while keeping every decision editable in ordinary MIDI/JSON.

## Fingering
Open strings:
- Violin I/II: G3 D4 A4 E5
- Viola: C3 G3 D4 A4
- Cello: C2 G2 D3 A3

A dynamic-programming path chooses a feasible string and finger semitone for each note in each explicit voice lane. The cost favors hand-frame continuity, smaller shifts and fewer unnecessary string crossings. Legato/expressive contexts penalize open strings when a practical stopped alternative exists; short/pizzicato contexts may prefer an open string.

The resulting graph records string name/index, finger semitone, position index, shift semitones and open-string state.

## Bowing
Bowing is phrase-aware and notation-aware:
- explicit `down-bow` / `up-bow` wins;
- a new phrase/rest resets toward down-bow;
- detached notes alternate bow direction;
- slur/legato-connected notes can stay in one bow;
- pizzicato disables bowed-pressure/change interpretation.

Pressure and contact point are deterministic functions of dynamics, articulation and expression modifiers. They are control priors, not measured bow-force values.

## Portamento
Explicit Portamento articulation gives route=1. Large connected legato shifts may receive a conservative inferred route. The runtime projects that route onto supported legato/transition/pitch-bend controls; it does not synthesize an untrained glissando model.

## Divisi Desk
Each explicit v4.1 voice lane receives a stable desk index 0..3. Desk affects only tiny deterministic ensemble separation in the current runtime.

## Physical MIDI Bus
- CC27 String
- CC28 Position
- CC29 Bow Direction
- CC30 Bow Change
- CC31 Bow Pressure
- CC33 Contact Point
- CC34 Portamento Route
- CC35 Divisi Desk

CC32 remains unused because it is Bank Select LSB.

## Acoustic honesty
v4.2 does not claim true per-string recorded timbre, real sul ponticello/sul tasto/col legno, or measured bow-force synthesis. These require actual acoustic/training capability. Unsupported techniques remain preserved as score semantics/warnings.
