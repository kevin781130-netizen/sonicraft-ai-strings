# SONICRAFT v4.8 Phrase Performance Critic & Auto-Repair

## Purpose
v4.8 adds a deterministic self-review pass after the complete v4.7 strings performance graph has been built.

The critic intentionally separates two questions:

1. **Is the performance-control plan structurally coherent/playable?** — v4.8 Critic.
2. **Which rendered candidate sounds best?** — existing Audio Judge.

The critic cannot auto-commit a final sonic winner.

## Structural dimensions and weights
- Bow Reserve: 20%
- Transition: 20%
- Vibrato: 15%
- Dynamics Arc: 15%
- Gesture Spikes: 15%
- Ensemble Alignment: 15%

Scores are 0–100 engineering diagnostics, not perceptual MOS scores.

## Candidate A — Conservative
Uses low smoothing strength, preserves transition topology, provides small bow-pressure relief, and minimally narrows ensemble spread.

## Candidate B — Balanced
Uses the strongest structural smoothing. If a phrase remains critically bow-starved, it may add one safe re-bow at a low-risk interior boundary and break that continuous transition link. This candidate is intended as the default structural repair, not an automatic audio winner.

## Candidate C — Expressive
Repairs discontinuities with moderate smoothing, then restores a slightly broader phrase apex and vibrato/dynamics movement.

## Candidate D — Original
The untouched v4.7 performance plan.

## Audio Judge handoff
`*.judge_queue.json` maps the four MIDI files into A/B/C/D slots. Render all four under the same model, seed, stage, microphone and runtime settings before judging.

The existing Audio Judge remains the final sonic authority.

## Acoustic honesty
No new acoustic data, transition samples, string recordings or trained preference model are added by v4.8. The critic acts only on performance-control data.
