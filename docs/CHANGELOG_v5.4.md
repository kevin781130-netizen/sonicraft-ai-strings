# SONICRAFT v5.4 Changelog

## Added
- Conductor-Steered A/B/C candidate generation
- Section-specific candidate profiles
- D-derived Dynamic ceiling clamp
- immutable note-identity steering assertion
- Bow Reserve recomputation after steering
- `*.candidate_steering.json`
- post-steer structural critic scores
- progressive per-section candidate render budget
- deferred candidate escalation on Audio margin < 0.025
- v5.4 compiler / auto-loop entrypoints
- native v5.4 candidate-budget contract

## Candidate budgets
- Intro: A/B/D, defer C
- Build: A/B/C/D
- Sustain: A/B/C/D
- Climax: B/C/D, defer A
- Release: A/B/D, defer C
- Resolution: A/B/D, defer C

## Preserved
- D Original untouched
- v5.3 Conductor Intent Lock
- v5.2 Global Coherence
- v5.1 selective repair
- v5.0 Shadow TCP/chunking
- v4.9 Repair Policy
- v13 state
- ParamID max 740
- no new CC family
- realtime/acoustic core byte-identical to v5.3
