# SONICRAFT v6.1 Reproducible Performance Checkpoint

## Purpose

v6.0 answers:

> Can SONICRAFT keep long-term evidence coherent?

v6.1 answers:

> Can SONICRAFT explain and reconstruct the exact control environment that generated an old performance candidate set?

## Checkpoint identity

Checkpoint schema: 1.

Checkpoint ID is the first 24 hexadecimal characters of SHA-256 over a path-independent canonical projection of immutable checkpoint input/compile bindings.

The identity projection:
- binds source content SHA-256, not source filename;
- binds raw SHA-256 for MIDI/binary artifacts;
- binds normalized SHA-256 for JSON artifacts;
- keeps raw JSON SHA/byte size in the Checkpoint for forensics but excludes them from the ID;
- normalizes the literal Evidence pin tag to avoid recursive `checkpoint ID -> pin tag -> checkpoint ID` dependence.

Therefore identical musical/control state can produce the same Checkpoint ID even when compiled in another directory with different Score/Policy filenames.

Final result data receives a separate `result_binding_sha256`. `load_checkpoint_v61` validates this binding whenever `output_state` exists, so post-round winner/Evidence/Policy/result metadata cannot be silently edited.

## Compiler code fingerprint

The checkpoint fingerprints the relevant source modules, including:
- v6.1 compiler
- score graph
- physical solver
- constraints
- ensemble
- gesture
- transition
- phrase
- critic/repair
- Repair Policy
- Conductor Intent / Steering
- Archetype Mixture
- Evidence Store
- Checkpoint runtime

This is stricter than checking only a public version string.

## Artifact hashing

Binary/MIDI:
- raw SHA-256

JSON:
- raw SHA-256
- normalized SHA-256

Normalized JSON replaces only machine-dependent path fields:
- source_score
- queue_dir
- policy_path
- persistent_policy_path

All other values remain authoritative.

## Evidence pin lifecycle

Creation:
- checkpoint reads v6.0 Store HEAD;
- validates all five namespace blobs;
- pins that commit with `checkpoint:<checkpoint_id>`.

Compaction:
- keeps recent commits;
- keeps HEAD;
- keeps every pinned commit;
- keeps blobs referenced by those commits.

Release:
- removes only the matching checkpoint tag.

Checkpoint deletion by itself does not automatically release a pin. Use the release command explicitly before deleting a checkpoint if retention is no longer required.

## Replay Verify

Replay is intentionally non-destructive.

The live Policy and live Evidence HEAD remain unchanged.

Replay uses a temporary Repair Policy reconstructed from the checkpoint payload, recompiles the score, and compares deterministic compile outputs.

The Evidence commit is read-only verified to prove the required history still exists.

## Restore

Restore is destructive by design and therefore explicit.

It:
1. verifies the checkpoint;
2. backs up current Repair Policy if present;
3. rolls Evidence Store/legacy namespace files to input commit;
4. writes exact checkpoint Repair Policy;
5. verifies the restored policy profile hash.

## Scope

This is a performance-control reproducibility layer.

It does not embed:
- audio
- MIDI bytes
- model weights

It does not claim bit-identical acoustic output.
