# SONICRAFT v3.8 Judge Memory / Personal Taste

v3.8 adds a local, explainable preference correction above the v3.7 objective Audio Judge. Favorite, Reject and manual Commit can contribute evidence when Learn My Choices is enabled. The profile stores only five weights, evidence and generation metadata in `Profiles/judge_memory_v38.json`; it stores no audio or MIDI.

The five dimensions are Dynamics, Attack, Transition, Stability and Safety. Safety weight is clamped non-negative. Personal correction is confidence-gated and bounded to ±0.12 around the objective Judge score; Safety below 0.20 cannot receive a positive taste bonus. One manual Commit contributes 1.35 evidence, which intentionally produces only about 9.86% confidence.

The v3.7 100-byte Judge result remains supported. v3.8 clients opt into a 144-byte result through the existing 8-byte Judge config reserved field. The service also exposes preference update/query/clear messages. A separate client worker handles network/profile synchronization so no JSON or socket IO occurs in the audio callback.
