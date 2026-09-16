# Release Schema 8: phrase-transition promotion

Schema 8 is the fail-closed release contract for Ai Strings builds that include the clean-room multi-note phrase fine-tune.

It extends Schema 7 acoustic promotion. It does not replace Sound Forge, codec tournament/ABX, generated-real ABX, provenance, or the REAL80/MODEL20 policy.

## Dual-source phrase provenance

Schema 8 deliberately records phrase supervision in two independent places.

First, renderer training derives `phrase_finetune_provenance` from the actual latent index. It is not a user-supplied release flag. If the index contains `phrase_family` rows, the checkpoint records a tamper-evident marker with `required_release_schema=8`, the root phrase-index SHA-256, phrase families/datasets, and a provenance ID. That marker is inherited through resume, ordinary distillation, reflow distillation, and shortcut training.

Second, `training_provenance.json` carries a separate `phrase_supervision` attestation. It binds the exact combined fine-tune index SHA-256 to the exact phrase-curriculum report SHA-256 and also declares `required_release_schema=8`. Create it from the curriculum evidence rather than editing it by hand:

```bash
python training/scripts/stamp_phrase_training_provenance.py \
  --provenance evidence/training_provenance.json \
  --curriculum-report datasets/processed/phrase_finetune/curriculum_report.json
```

Both `build_release_model_manifest.py` and `commercial_release_gate.py` validate the training-provenance attestation and both shipping renderer checkpoint lineages. If either source declares phrase supervision, Schema 7-or-older is rejected. Under Schema 8, training provenance, curriculum evidence, HQ lineage, and Compact lineage must all name the same fine-tune index SHA-256.

These hashes are tamper-evident consistency checks, not digital signatures. They are intended to catch missing provenance, schema downgrade, stale/mismatched evidence, and accidental or partial artifact rewriting; they do not claim cryptographic authenticity against an actor who can deliberately rewrite every unsigned artifact consistently.

## Required transition evidence

A Schema 8 release requires all of the following in addition to Schema 7 evidence:

- `training_provenance.json.phrase_supervision` stamped from the exact phrase curriculum report;
- `phrase_curriculum_report.json` from `build_phrase_finetune_index.py`;
- one passed `transition_promotion_v1` report for the shipping HQ renderer;
- one independently passed `transition_promotion_v1` report for the shipping Compact/Frontier renderer;
- a transition seal on each exact renderer checkpoint.

The phrase curriculum report records `output_index_sha256`. That digest must equal the training-provenance `phrase_supervision.source_index_sha256` and the root `phrase_source_index_sha256` embedded in both renderer lineages. The training-provenance attestation must also contain the SHA-256 of the exact curriculum report bytes.

HQ and Compact must be evaluated on the same held-out phrase latent index, but their promotion IDs must be different because each promotion is checkpoint-specific.

The codec decoder is not transition-sealed; this gate concerns renderer phrase/transition behavior.

## Seal both renderer checkpoints

```bash
python training/scripts/seal_transition_promotion.py \
  --checkpoint Models/ballad_renderer_hq_v20_best.pt \
  --promotion evidence/transition_promotion_hq.json \
  --curriculum datasets/processed/phrase_finetune/curriculum_report.json

python training/scripts/seal_transition_promotion.py \
  --checkpoint Models/ballad_renderer_frontier_v20_shortcut.pt \
  --promotion evidence/transition_promotion_compact.json \
  --curriculum datasets/processed/phrase_finetune/curriculum_report.json
```

The sealer rejects underpowered/failed transition evidence before touching the checkpoint. It also validates checkpoint `phrase_finetune_provenance` and requires the root phrase-index SHA-256 to equal curriculum `output_index_sha256`. A valid seal records the exact promotion-report SHA-256, pre-seal candidate checkpoint SHA-256, phrase-curriculum SHA-256, held-out index SHA-256, phrase source-index SHA-256, promotion ID, and a digest of model/EMA/decoder tensors. Saving the seal is rejected if tensor bytes change.

## Build the Schema 8 manifest

Use all normal Schema 7 arguments plus the three Schema 8 evidence arguments:

```bash
python training/scripts/build_release_model_manifest.py \
  --schema 8 \
  --model-dir Models \
  --provenance evidence/training_provenance.json \
  --metrics evidence/release_metrics.json \
  --sound-forge-report evidence/sound_forge.json \
  --codec-tournament evidence/codec_tournament.json \
  --codec-abx-report evidence/codec_abx.json \
  --acoustic-segments evidence/acoustic_segments.json \
  --generated-real-abx evidence/generated_real_abx.json \
  --acoustic-promotion evidence/acoustic_promotion.json \
  --phrase-curriculum-report datasets/processed/phrase_finetune/curriculum_report.json \
  --hq-transition-promotion evidence/transition_promotion_hq.json \
  --compact-transition-promotion evidence/transition_promotion_compact.json \
  --approve
```

Before writing `release_model_manifest.json`, the builder verifies:

- a valid `training_provenance.json.phrase_supervision` attestation;
- exact curriculum-report SHA-256 matches the training-provenance attestation;
- exact fine-tune index SHA-256 matches training provenance, curriculum evidence, HQ lineage, and Compact lineage;
- valid tamper-evident phrase lineage on HQ and Compact;
- exact transition promotion ID and promotion-report hash;
- exact pre-seal candidate checkpoint hash recorded in the seal;
- exact phrase-curriculum hash and held-out index hash;
- current tensor digest equals the sealed tensor digest;
- HQ and Compact use the same held-out phrase corpus;
- REAL80/MODEL20 remains intact.

Evidence is staged under distinct names in `Models/` so HQ and Compact promotion reports cannot overwrite each other.

## Commercial release gate

```bash
python training/scripts/commercial_release_gate.py --model-dir Models
```

The commercial gate independently reopens the staged `training_provenance.json` plus HQ and Compact checkpoints. A phrase attestation or renderer phrase lineage under Schema 7 or older causes immediate rejection, even if the manifest was hand-authored. For Schema 8 it also requires the attestation ID, curriculum-report hash, exact fine-tune index hash, renderer lineage, promotion IDs, transition seals, and held-out phrase index to agree across the staged artifacts.

A Schema 7 manifest remains valid only when neither training provenance nor either renderer lineage declares phrase supervision.

## Dependency-light smoke

Run the same one-command validator used by the release-contract workflow:

```bash
python training/run_release_contract_smoke.py
```

It syntax-compiles the release/phrase modules and runs five checks: Schema 8 transition-evidence validation, checkpoint-lineage inheritance/tamper validation, independent training-provenance validation, a transition-sealer contract test, and an end-to-end dry run that invokes the real sealer, manifest builder, and commercial release gate with tiny fixture checkpoints. The negative paths cover bad curriculum/index binding and a stripped-checkpoint/hand-edited Schema 7 downgrade whose file hashes remain valid; both must be rejected before release.
