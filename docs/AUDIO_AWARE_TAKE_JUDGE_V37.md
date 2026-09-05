# SONICRAFT v3.7 Audio-Aware Take Judge

v3.7 adds a non-realtime A/B/C/D render-and-judge path on top of v3.6 Smart Comp Timeline.

## Execution model
- Plug-in requests Judge for the current Performance Memory phrase.
- Shadow Renderer worker keeps the request outside the realtime audio callback.
- Renderer service derives deterministic A/B/C/D nonces using the v3.2 contract.
- The same 8-bit nonce ultimately used by the renderer is preserved.
- Existing waveform cache is reused; repeat Judge calls do not blindly rerender all four takes.
- Event-only score/control history is retained for 90 seconds to support pinned-phrase review.

## DSP metrics
The NumPy-only Judge analyzes the master stereo pair, not all virtual stage feeds:
- Dynamics Contour: rendered log-energy contour vs authored control intent.
- Attack Consistency: onset-rise consistency around authored note-on locations.
- Transition Smoothness: unexplained derivative bursts / broadband chatter away from authored onsets.
- Energy Stability: short-window log-energy volatility.
- Safety: near-clipping density and headroom.

Overall weights: 29% Dynamics, 23% Attack, 20% Transition, 16% Stability, 12% Safety.

These are engineering/score-adherence metrics. They are **not** a learned aesthetic preference model and do not claim to judge emotional or timbral taste.

## Human review
- Favorite adds dominant winner priority.
- Reject removes a candidate.
- If all candidates are rejected, there is no valid winner.

## Smart Comp integration
If a valid Judge result matches the exact current phrase start sample:
- Smart Timeline current Smart slot shows the Judge winner.
- Smart Audition uses the Judge winner.
- Smart Commit uses the Judge winner.
Otherwise v3.6 heuristic Smart Rank remains the fallback.

## Stale-result protection
Judge results carry their rendered start sample. Audition/Commit requires exact equality with the current phrase sample-range start, preventing a result from a previously browsed phrase being committed to another phrase.

## State
Judge outputs are derived/ephemeral and are intentionally not serialized. State schema remains v12. Persistent Comp, Performance Memory and Smart Rank state continue to use the existing v12 contract.
