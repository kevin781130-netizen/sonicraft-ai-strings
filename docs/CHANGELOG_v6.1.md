# SONICRAFT v6.1 Changelog

## Added
- finalized result tamper rejection
- finalized output-state `result_binding_sha256` validation
- same-state cross-directory Checkpoint ID stability
- path-independent Checkpoint ID projection
- project-local Reproducible Performance Checkpoint schema 1
- source score SHA-256 binding
- compiler source-code fingerprint binding
- v6.0 Evidence input commit binding
- five Evidence namespace hash binding
- exact v4.9 Repair Policy payload/generation/profile-hash binding
- Conductor Intent hash binding
- Candidate Steering Intent hash binding
- 12 deterministic compile artifact hashes
- raw MIDI SHA-256 + normalized JSON SHA-256
- non-destructive Replay Verify
- explicit Evidence + Policy Restore
- automatic pre-restore Repair Policy backup
- input/output state separation
- post-round result binding SHA-256
- Evidence commit pinning across compact
- explicit Checkpoint pin release
- PERFORMANCE_CHECKPOINT_V61.bat
- v6.1 compiler / Auto-Loop entrypoints
- native Checkpoint contract

## v6.0 compatible extension
- Evidence Store schema remains 1
- optional `pins` map added
- compact preserves pinned commits and their blobs
- export/import/status include pin metadata

## Preserved
- v6.0 five-namespace Evidence semantics
- v5.9 Soft Mixture mathematics
- v5.8 Archetype evidence
- v5.7 Similarity Transfer
- v5.6 Counterfactual Auditor
- v5.5 Candidate Utility
- v5.4 Conductor Steering
- v5.3 Conductor Intent
- v5.2 Global Coherence
- v5.1 Selective rendering
- v4.9 Repair Policy remains logically separate from Evidence
- merged-vs-D full Audio verification
- state v13
- ParamID max 740
- no new MIDI CC
- realtime/acoustic core byte-identical to v6.0

## Explicit non-claim
- Checkpoint Replay does not claim bit-identical audio reproduction.
