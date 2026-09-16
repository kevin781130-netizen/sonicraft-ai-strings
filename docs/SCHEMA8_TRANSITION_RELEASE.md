# Release Schema 8: phrase-transition promotion

Schema 8 is the fail-closed release contract for Ai Strings builds that include the clean-room multi-note phrase fine-tune.

It extends Schema 7 acoustic promotion. It does not replace Sound Forge, codec tournament/ABX, generated-real ABX, provenance, or the REAL80/MODEL20 policy.

## Required transition evidence

A Schema 8 release requires all of the following in addition to Schema 7 evidence:

- `phrase_curriculum_report.json` from `build_phrase_finetune_index.py`;
- one passed `transition_promotion_v1` report for the shipping HQ renderer;
- one independently passed `transition_promotion_v1` report for the shipping Compact/Frontier renderer;
- a transition seal on each exact renderer checkpoint.

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

The seal records the exact promotion-report SHA-256, pre-seal candidate checkpoint SHA-256, phrase-curriculum SHA-256, held-out index SHA-256, promotion ID, and a digest of model/EMA/decoder tensors. Saving the seal is rejected if tensor bytes change.

## Build the Schema 8 manifest

Use all normal Schema 7 arguments plus the three Schema 8 arguments:

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

Before writing `release_model_manifest.json`, the builder reopens both renderer checkpoints and verifies:

- exact transition promotion ID;
- exact promotion report hash;
- exact pre-seal candidate checkpoint hash recorded in the seal;
- exact phrase-curriculum hash;
- exact held-out index hash;
- current tensor digest equals the sealed tensor digest;
- HQ and Compact use the same held-out phrase corpus;
- REAL80/MODEL20 remains intact.

Evidence is staged under distinct names in `Models/` so HQ and Compact promotion reports cannot overwrite each other.

## Commercial release gate

```bash
python training/scripts/commercial_release_gate.py --model-dir Models
```

For Schema 8 the gate rejects the release if `phrase_finetune` is not true, either transition report is absent/failed/underpowered, promotion identities do not match the renderer file entries, curriculum evidence drifts outside the MODELED lane, or HQ/Compact were evaluated on different held-out phrase indexes.

A Schema 7 manifest remains valid for releases that did not use this phrase fine-tune path. A phrase-fine-tuned release must be built as Schema 8; downgrading the manifest schema is not an acceptable way to bypass the transition gate.

## Dependency-light smoke

```bash
cd training
python smoke_release_schema8.py
```

The smoke test covers a valid pair plus rejection of shared checkpoint promotion IDs, mismatched held-out indexes, MODELED-lane drift, and a failed renderer promotion.
