# SONICRAFT v6.0 Validation — Unified Evidence Store / Memory Consolidation

Validated 2026-09-03 in the available Linux environment.

## v6.0 Core PASS

Unified transaction namespaces:

1. utility_v55
2. audit_v56
3. similarity_v57
4. archetype_v58
5. mixture_v59

v4.9 Repair Policy remains outside the Store by design.

Core governance PASS:
- Store schema 1
- canonical JSON namespace hashing
- SHA-256 content addressing
- zlib-compressed blobs
- content deduplication
- atomic Store file replacement
- atomic five-namespace transaction commit
- first-run empty legacy initialization
- bootstrap from existing legacy memories
- startup hash verification
- whole-set rollback on partial/drifted state
- quarantine of drifted/invalid legacy bytes
- recursive structural contamination guard
- full rollback
- per-namespace restore
- export
- validated import
- compact / unreferenced blob removal
- default commit retention 32
- path-independent persistent Store payload
- legacy v5.5-v5.9 JSON compatibility

## Transaction / rollback / quarantine fixture

Initial state:
- five legacy memory files absent
- Unified Store absent

First bootstrap:
- five compatible v1 legacy namespace files created
- one complete Store transaction captured

Second transaction:
- only Utility + Audit changed
- unchanged Similarity / Archetype / Mixture snapshots reused content-addressed blobs

Partial-crash simulation:
- only Utility legacy JSON manually changed to generation 99
- Store verification detected `drift`
- drifted bytes were preserved in quarantine
- all five namespaces were restored to the last complete HEAD
- partial `corrupt_partial` context disappeared after recovery

Contamination simulation:
- structural `audio` field injected into Utility namespace
- commit rejected with `forbidden_structural_field`
- contaminated state never became Store HEAD

Rollback:
- a later Mixture commit was created
- full rollback restored the earlier transaction
- Mixture generation returned to the earlier value

Export/import:
- exported Store imported into a clean Store
- HEAD and namespace hash map matched
- every referenced blob was decompressed, hash-checked, JSON-parsed and schema-validated before replacement

Compaction fixture:
- recent history retained
- unreferenced blobs removed
- current HEAD remained readable

Representative unit result:
- commits after compact: 2
- live blobs: 6
- quarantine records: 1
- unreferenced blobs removed: 2

## Auto-Loop transaction integration PASS

v6.0 Auto-Loop sequence:

1. resolve five legacy paths
2. open Unified Evidence Store
3. bootstrap/recover transaction state
4. instantiate v5.5-v5.9 legacy memory objects
5. run existing local prediction / audit / learning
6. capture all five legacy memories as one transaction
7. immediately verify all five hashes against HEAD
8. only then continue downstream Conductor / merge / full-pair verification

Integration fixture:
- v5.9 Soft Mixture cold Context retained the same B / C / D local budget
- A remained Zero-Render
- Mixture evidence: 1.85181
- final local winner: B
- merged-vs-D verification: PASS
- estimated total render fraction: ~0.88
- Store commits after round: 2 (bootstrap + local-evidence transaction)

Startup drift simulation after the accepted round:
- Utility legacy file manually changed to generation 999
- next Store bootstrap detected Utility drift before new memory objects were instantiated
- Utility restored to committed generation
- injected `partial_crash_drift` context removed
- Store returned to all-five `match`
- quarantine count increased to 1

## Compiler capability PASS

v6.0 compiler Judge Queue advertises:
- five evidence namespaces
- atomic multi-namespace commit
- rollback
- quarantine
- export/import
- legacy JSON compatibility

The musical compile pipeline remains v5.9-compatible.

## Management entrypoint PASS

`EVIDENCE_STORE_V60.bat` exposes:
- status
- verify
- compact
- export
- rollback

Python manager also exposes validated import through the runtime API.

## Backward musical regressions PASS

### v5.9 Soft Archetype Mixture
- boundary mixture:
  - Intimate 0.447476
  - Ballad 0.387907
  - Chamber 0.164617
- mixture confidence: 0.812155
- cold-start Top-2 + D PASS
- hidden B -> A false prune gain: 0.050000024
- weighted component trust calibration PASS
- v5.8 / v5.7 isolation PASS

### v5.8 Archetype
- cold-start Archetype evidence: 2.410739 in unit fixture
- Top-2 + D PASS
- hard-Archetype hidden false-prune trust 1.0 -> 0.56 PASS

### v5.7 Similarity Transfer
- transfer evidence: 4.0
- transfer confidence: 0.627627
- donor high-risk block PASS

### v5.6 Counterfactual Auditor
- interval / false-prune / disable / recovery PASS
- hidden B -> A gain: 0.050000024
- audit fixture cost ~1.007

### v5.5 Candidate Utility
- high-confidence Zero-Render PASS
- cost fraction ~0.75
- predictor/audio disagreement escalation PASS

### v5.4 Conductor Steering
- Climax B/C: ~0.7998 / 0.8186
- Resolution A/B: ~0.5121 / 0.5212
- progressive skip fixture cost ~0.88

### v5.3 Conductor Intent
- five-section fixture
- intended Climax = Section 4
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
- >45 s chunk/crossfade PASS
- 2 chunks
- 404000 frames

The v6.0 integration fixture initially encountered the previously observed fixed-port mock-renderer startup `rc=1`.
No Renderer code was changed.
The same integration test was rerun on a clean port and PASS.

### v4.9
- Repair Policy memory/gates PASS

### v4.8
- D: 34.314
- A: 72.747
- B: 76.773
- C: 73.207
- best structural repair: B

### v4.7 / v4.6
- Phrase Torch/NumPy parity PASS
- max phrase rate 5.7 Hz
- phrase depth 23.433 cents
- Transition parity target ~129.72 ms

### ORT
- no-Torch wiring PASS
- 12000 x 34
- peak ~0.404252

## Release-contract forward compatibility PASS

Public release/version contracts v5.0 through v5.9 accept current v6.0 while continuing to validate their historical runtime files.

v6.0 source/release contract PASS.

## Native PASS

Clean VST-independent CMake configure/build completed to 100%.

Native PASS:
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
- SonicraftInProcessEngineSmoke:
  - 9600 frames
  - 34 channels
  - peak ~0.0705933

## Promotion Guard PASS

- promotion binding PASS
- intentional tamper rejected with `renderer_binding_failed`

## Realtime/acoustic non-regression

The following v6.0 files are byte-identical to packaged v5.9:

- runtime/renderer_service.py
- runtime/model_backend.py
- runtime/control_builder_np.py
- runtime/ort_model_backend.py
- src/processor.cpp
- src/processor.h
- src/controller.cpp
- src/ids.h

Therefore v6.0 changes persistent evidence governance only.

## Integrity

- UIDESC XML parses
- explicit numeric ParamID collisions: 0
- highest explicit ParamID base: 740
- project state: v13
- CMake version: 6.0.0
- no new MIDI CC family
- installer/prebuilt includes:
  - evidence_store_v60.py
  - compile_musicxml_strings_v60.py
  - auto_loop_strings_v60.py
  - COMPILE_MUSICXML_STRINGS_v60.bat
  - AUTO_LOOP_STRINGS_v60.bat
  - EVIDENCE_STORE_V60.bat

## Honest release boundary

Not validated in this environment:
- rebuilt v6.0 VST3 binary
- Steinberg Validator
- real Cubase host test
- real Studio One host test
- Windows filesystem atomic-rename / permission / antivirus interaction
- signed commercial installer
- macOS / AU / AAX / ARA

No new acoustic training data or weights were added.
