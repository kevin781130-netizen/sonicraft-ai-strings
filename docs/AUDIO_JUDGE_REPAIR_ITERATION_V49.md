# SONICRAFT v4.9 Audio Judge Repair Iteration

## Separation of authorities
v4.9 keeps three layers separate.

1. **Structural Critic** — score/control-domain diagnostics.
2. **Objective Audio Judge** — rendered-audio dynamics, attack, transition, stability and safety.
3. **Personal Judge Memory** — the pre-existing Favorite/Reject/Commit taste layer.

Only layer 2 updates Repair Policy. Layer 3 remains user taste and is not silently converted into repair engineering rules.

## Repair Policy
The local profile stores five bounded values:
`smoothing`, `bow_relief`, `transition`, `ensemble_tightness`, `expressive_apex`.

Winner targets are intentionally interpretable:
- A -> less aggressive repair.
- B -> stronger smoothing/bow/transition/alignment repair.
- C -> preserve more expressive apex.
- D -> back away from repair because Original beat all repairs.

## Learning gate
Required:
- 4 comparable renders,
- margin >= 0.025,
- safety >= 0.35,
- overall >= 0.35,
- matching policy generation + hash.

The stale-profile check prevents late R1 audio from modifying an already-learned R2/R3 policy.

## Candidate-specific judging
The Audio Judge adapter parses each candidate MIDI independently and reconstructs note onsets plus authored dynamics/control intent in sample time. A is judged against A's MIDI, not D's MIDI.

## Iteration cap
Accepted learning can create the next round automatically up to round 6. This limits runaway optimization and forces a human/DAW checkpoint before indefinite cycling.

## Renderer boundary
v4.9 consumes actual WAV renders. It does not claim DAW automation or automatic Cubase/Studio One rendering in the current source-only validation environment.
