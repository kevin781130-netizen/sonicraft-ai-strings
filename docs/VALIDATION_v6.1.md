# SONICRAFT v6.1 Validation — Reproducible Performance Checkpoint / Policy–Evidence Binding

Validated 2026-09-03 in the available Linux environment.

## v6.1 Core PASS

Checkpoint schema: 1.

A project-local checkpoint binds:
- source score SHA-256
- SONICRAFT release version
- compiler code fingerprint
- pre-round v6.0 Evidence Store commit
- all five Evidence namespace hashes
- exact v4.9 Repair Policy payload
- Repair Policy generation / evidence / profile hash
- Conductor Intent hash
- Candidate Steering Intent hash
- twelve deterministic compile artifact hashes
- post-round Evidence + Policy state after finalization
- result decision digest and merged/final artifact hashes where available

No Audio or MIDI bytes are embedded.

## Strict real-compiler replay fixture PASS

Using the unmodified v6.1 compiler:

1. Created five v6.0 legacy Evidence namespace files and one bootstrap transaction.
2. Compiled a MusicXML fixture with v6.1.
3. Captured a checkpoint against the bootstrap Evidence HEAD and exact Repair Policy snapshot.
4. `verify` confirmed:
   - source SHA match
   - compiler code fingerprint match
   - Evidence commit exists
   - all five Evidence namespace hashes match
   - current Policy matches input state
   - all 12 compile artifacts match
5. `replay` reconstructed the checkpoint Repair Policy in a temporary directory.
6. Recompiled the score with no live state mutation.
7. All four MIDI artifacts matched exact raw SHA-256.
8. JSON sidecars matched normalized SHA-256; raw JSON SHA may differ only when local path strings differ.
9. Conductor Intent hash matched exactly.

Final regression additionally compiled the same Score/Policy/Evidence state in a different directory with different Score/Policy filenames:
- normalized compile identity matched;
- Checkpoint ID remained identical;
- raw path-bearing JSON bytes were allowed to differ;
- duplicate copies of the same semantic Checkpoint reused one Evidence pin tag.

Representative final core regression checkpoint ID:
- `7ef647e359a79403a9337474`

## Artifact tamper detection PASS

Repair B MIDI was manually appended with extra bytes.

`verify` immediately reported:
- `compile_artifacts_ok = false`
- `midi_B.ok = false`

Restoring the original MIDI bytes returned Verify to PASS.

## Finalized result-binding tamper detection PASS

A finalized Checkpoint receives a separate:

`result_binding_sha256 = SHA256(canonical output_state)`

The fixture finalized a result, then manually changed the stored winner from B to A without updating the binding.

`load_checkpoint_v61` rejected it with:

`checkpoint_result_binding_mismatch`

Therefore immutable compile/input identity and post-round result state are independently tamper-evident.

## Live state advancement / non-destructive replay PASS

After checkpoint capture:
- Evidence Store was advanced through additional transactions;
- Repair Policy learned a new accepted B result and changed profile hash.

Expected behavior:
- current live Policy no longer matched checkpoint input Policy;
- checkpoint remained replay-ready;
- Replay used the embedded old Policy snapshot;
- Replay PASS;
- live Evidence HEAD remained unchanged;
- live Repair Policy remained unchanged by Replay.

## Evidence commit pinning PASS

A long-term Checkpoint automatically pins its input Evidence commit with:

`checkpoint:<checkpoint_id>`

Test sequence:
- checkpoint input commit created;
- Store advanced through five additional transactions;
- `compact(retain=2)` executed;
- old checkpoint input commit was older than the normal retention window;
- pinned commit remained present;
- blobs required by that commit remained readable;
- Replay / Restore remained available.

Representative compact result:
- retained commits: 3
  - two recent commits
  - one old pinned Checkpoint commit

Explicit `release` removed the Checkpoint pin successfully.

After release, future compaction is allowed to remove that old commit when it is no longer HEAD/recent.

## Explicit Environment Restore PASS

Restore was executed after both Evidence and Repair Policy had advanced.

Result:
- current Repair Policy backed up to `*.pre_v61_restore.bak`;
- Evidence Store HEAD moved to checkpoint input commit;
- all five legacy Evidence namespace files restored together;
- exact Repair Policy payload restored;
- Repair Policy profile hash matched checkpoint input hash;
- v6.0 `verify_legacy` returned all-five match.

Restore is explicit and mutating.
Replay is non-destructive.

## JSON path normalization PASS

MIDI artifacts use raw SHA-256.

JSON sidecars use both raw and normalized SHA-256.

Only these machine-location fields are normalized:
- `source_score`
- `queue_dir`
- `policy_path`
- `persistent_policy_path`

Deterministic output filenames, expected render filenames, musical values, control values, hashes and intent data remain part of the comparison.

This allows replay from another local directory without treating a path change as a musical mismatch.

Checkpoint identity also excludes:
- source filename;
- raw JSON SHA-256;
- raw JSON byte length.

Those raw values remain stored for forensic inspection, but the Checkpoint ID is based on source content SHA, deterministic MIDI raw hashes, normalized JSON hashes, Evidence/Policy/Compiler/Intent bindings and other path-independent immutable fields.

## Auto-Loop integration PASS

The v6.1 Auto-Loop integration fixture preserved the existing v5.9 cold-start behavior:
- target: `build|latent_playability+transition`
- mixture components:
  - Intimate 0.447476
  - Ballad 0.387907
  - Chamber 0.164617
- mixture evidence: 1.85181
- local budget: B / C / D
- A: Zero-Render
- local winner: B
- estimated total render fraction: ~0.88

v6.1 additionally:
- created a Checkpoint immediately after compile and before local Evidence use;
- input Evidence commit differed from finalized output Evidence commit;
- input Repair Policy hash differed from finalized output Policy hash after accepted learning;
- finalized result binding was written to the Checkpoint;
- final report referenced checkpoint ID/path;
- v6.0 startup drift recovery still worked after Checkpoint integration.

Representative final Auto-Loop regression checkpoint ID:
- `79fac869028e2d2ab0aaa0e1`

The Auto-Loop cold-start fixture intentionally overrides Archetype/Mixture sidecars to force a stable synthetic mixture; strict real-compiler Replay is therefore validated separately by the core Checkpoint fixture rather than weakening the production replay contract.

## v6.0 Evidence Store regressions PASS

After adding optional Checkpoint pins, existing v6.0 behavior remains PASS:
- bootstrap
- content-addressed SHA-256 blobs
- zlib compression
- deduplication
- transaction capture
- drift detection
- quarantine
- whole-set rollback
- contamination rejection
- export/import
- compact
- Auto-Loop transactional integration
- source/release contracts

Evidence Store schema remains 1.

Pin metadata is optional and backward-compatible.

## v5.9 → v4.6 musical regressions PASS

### v5.9 Soft Archetype Mixture
- Intimate 0.447476
- Ballad 0.387907
- Chamber 0.164617
- mixture confidence 0.812155
- cold-start Top-2 + D PASS
- hidden B -> A false-prune gain 0.050000024 PASS

### v5.8 Archetype
- cold-start evidence 2.410739 in unit fixture
- Top-2 + D PASS
- hidden false-prune trust 1.0 -> 0.56 PASS

### v5.7 Similarity Transfer
- transfer evidence 4.0
- transfer confidence 0.627627
- donor high-risk block PASS

### v5.6 Counterfactual Auditor
- scheduled hidden B -> A audit PASS
- counterfactual gain 0.050000024
- audit interval 12
- cost fraction ~1.007

### v5.5 Candidate Utility
- high-confidence Zero-Render PASS
- cost fraction ~0.754
- predictor/audio disagreement escalation PASS
- escalation cost fraction ~1.007

### v5.4 Conductor Steering
- Climax B/C ~0.7998 / 0.8186
- Resolution A/B ~0.5121 / 0.5212
- progressive skip fixture ~0.88

### v5.3 Conductor Intent
- five sections
- intended Climax Section 4
- local C -> selected B
- Intent score 100.0

### v5.2 Global Coherence
- bad A score 48.027754
- selected B
- coherence 99.4176

### v5.1 Selective Phrase
- phrase localization / coverage fallback PASS
- MIDI merge boundary PASS

### v5.0 Shadow
- >45 second chunk/crossfade PASS
- 2 chunks
- 404000 frames

### v4.9
- Repair Policy memory/gates PASS

### v4.8
- D 34.314
- A 72.747
- B 76.773
- C 73.207
- best B

### v4.7 / v4.6
- Phrase Torch/NumPy parity PASS
- max phrase rate 5.7 Hz
- phrase depth 23.433 cents
- Transition parity target ~129.72 ms

### ORT
- no-Torch wiring PASS
- 12000 × 34
- peak ~0.404252

## Release-contract forward compatibility PASS

Public release/version contracts v5.0 through v6.0 accept current v6.1 while continuing to validate their historical files and entrypoints.

v6.1 source/release contracts PASS.

## Native PASS

Clean VST-independent CMake configure/build completed to 100%.

Native PASS:
- SonicraftPerformanceCheckpointSmokeV61
- SonicraftEvidenceStoreSmokeV60
- SonicraftArchetypeMixtureSmokeV59
- SonicraftPerformanceArchetypeSmokeV58
- SonicraftContextSimilarityTransferSmokeV57
- SonicraftCounterfactualAuditorSmokeV56
- SonicraftCandidateUtilitySmokeV55
- SonicraftConductorSteeringSmokeV54
- SonicraftConductorIntentSmokeV53
- SonicraftGlobalCoherenceSmokeV52
- SonicraftSelectivePhraseSmokeV51
- SonicraftStringRepairPolicySmokeV49
- SonicraftStringPerformanceCriticSmokeV48
- SonicraftStringPhraseSmokeV47
- SonicraftStringTransitionSmokeV46
- SonicraftStringGestureSmokeV45
- SonicraftStringEnsembleSmokeV44
- SonicraftStringConstraintSmokeV43
- SonicraftStringPhysicalSmokeV42
- SonicraftStringExpressionSmokeV41
- SonicraftInProcessEngineSmoke
  - 9600 frames
  - 34 channels
  - peak ~0.0705933

## Promotion Guard PASS

- promotion binding PASS
- intentional tamper rejected with `renderer_binding_failed`

## Realtime/acoustic non-regression

The following v6.1 files are byte-identical to packaged v6.0:
- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

Therefore v6.1 adds project reproducibility / state binding without changing realtime acoustic behavior.

## Integrity

- UIDESC XML parses
- explicit numeric ParamID collisions: 0
- highest explicit ParamID base: 740
- project state: v13
- CMake version: 6.1.0
- no new MIDI CC family
- installer/prebuilt includes:
  - performance_checkpoint_v61.py
  - compile_musicxml_strings_v61.py
  - auto_loop_strings_v61.py
  - COMPILE_MUSICXML_STRINGS_v61.bat
  - AUTO_LOOP_STRINGS_v61.bat
  - PERFORMANCE_CHECKPOINT_V61.bat
  - existing EVIDENCE_STORE_V60.bat

## Honest release boundary

v6.1 Replay proves deterministic compiler/control-state reproduction under the same source/runtime code contract.

It does NOT claim bit-identical acoustic output.

Not validated in this environment:
- rebuilt v6.1 VST3 binary
- Steinberg Validator
- real Cubase host test
- real Studio One host test
- Windows cross-directory replay QA
- Windows policy backup/restore permissions
- Windows antivirus / backup-software filesystem interference
- signed commercial installer
- macOS / AU / AAX / ARA
- bit-identical audio across GPU/runtime/model changes

No new acoustic training data or weights were added.
