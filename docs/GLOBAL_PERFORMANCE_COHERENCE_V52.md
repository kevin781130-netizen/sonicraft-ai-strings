# SONICRAFT v5.2 Global Performance Coherence Guard

## Problem

A local repair system can over-optimize individual phrases. A louder, tighter, more vibrato-heavy repair may win one isolated window while making the complete piece sound like several different performers were edited together.

v5.2 introduces a whole-piece graph guard after Local Audio Judge and before final selective merge.

## Baseline-relative coherence

The guard does not demand uniformity.

For every stable phrase/lane sequence it compares:
- the D Original phrase-to-phrase jump;
- the proposed merged phrase-to-phrase jump.

Only *new excess discontinuity* beyond D plus a tolerance is penalized.

This preserves written contrasts, section changes, and intentional long-line development.

## Dimensions

### Dynamic trajectory
Mean and peak Gesture Dynamics Energy.

### Vibrato character
Gesture Vibrato Depth plus phrase-level Vibrato Rate.

### Bow energy
Bow Pressure plus minimum phrase Bow Reserve.

### Desk looseness
Variation in Ensemble Attack Offset.

### Transition density
Number of linked transitions per phrase plus transition continuity/duration treatment.

### Section role
Lead / Inner / Foundation distribution from the existing ensemble role metadata.

## Candidate search

For each local window:
- local Audio winner is retained;
- one runner-up may be considered when within 0.075 Overall;
- D Original is kept as a safety candidate when it clears Safety/Overall floors.

With at most six selective windows this keeps the search bounded while still allowing a globally coherent combination.

Passing thresholds:
- Global Coherence score >= 82
- Maximum normalized edge excess <= 1.45

## Full pair verification

Graph coherence is not a substitute for audio.

At selective convergence the merged MIDI and D Original are both rendered full-length. Each Audio Judge uses its own MIDI intent.

Merged passes when:
- Overall is no more than 0.025 below D;
- Safety is no more than 0.04 below D.

Failure triggers the full A/B/C/D fallback.

## Authority

Local Audio Judge proposes phrase-level sonic winners.
Global Coherence Guard may substitute only near-scoring candidates to preserve whole-piece identity.
Full pair verification protects whole-song rendered behavior.
The existing full A/B/C/D fallback remains the final safety route.

No acoustic model training occurs in v5.2.
