# Schema 8 production runbook

This is the operational handoff for the clean-room phrase release path. The release
contract is already implemented; production artifacts are intentionally generated
outside Git.

## 1. Create one release plan

Copy `training/schema8_release_plan.example.json` to a local release plan and edit
only its paths/codec/seed. The status checker and post-GPU runner consume the same
file so evidence paths cannot drift between commands.

```bash
python training/scripts/schema8_release_status.py \
  --plan schema8_release_plan.local.json
```

Typical stages are:

- `WAITING_FOR_STATIC_INPUTS`
- `WAITING_FOR_GPU_TRAINING`
- `WAITING_FOR_TRANSITION_EVAL_OR_PROMOTION`
- `WAITING_FOR_HUMAN_ABX`
- `READY_FOR_SCHEMA8_FINALIZATION`
- `RELEASE_MANIFEST_PRESENT`

The status command is informational only. Preflight and release gates remain
authoritative.

## 2. GPU handoff

The two release artifacts that must come from model training are the exact HQ and
Compact/Frontier candidate checkpoints named by the plan. Keep the pre-phrase HQ
and Compact baselines too; transition evaluation is paired against those exact
baselines.

Do not seal candidate checkpoints during training. Transition promotion reports
bind the *pre-seal file SHA-256* and the sealer adds metadata only after all evidence
has passed.

## 3. Deterministic transition evaluation and promotion

After both trained candidates exist:

```bash
python training/scripts/run_schema8_post_gpu.py \
  --plan schema8_release_plan.local.json \
  --phase evaluate

python training/scripts/run_schema8_post_gpu.py \
  --plan schema8_release_plan.local.json \
  --phase promote
```

The runner uses one held-out phrase index and one seed from the plan for all four
evaluations (HQ baseline/candidate and Compact baseline/candidate).

## 4. Generated-vs-real listener ABX

Use **rights-cleared held-out real recordings** as the real side. The clean-room
synthetic phrase holdout is transition evidence and must not be relabeled as a real
acoustic anchor. Render matched candidate audio from the exact trained release
checkpoint through the shipping renderer/codec path, then prepare the blind packet:

```bash
python training/scripts/prepare_blind_abx.py \
  --real-dir evidence/abx_audio/real \
  --generated-dir evidence/abx_audio/generated \
  --out evidence/generated_real_abx_packet \
  --min-trials 20

python training/scripts/validate_blind_abx_packet.py \
  --packet evidence/generated_real_abx_packet
```

Candidate-audio rendering is intentionally a post-training production artifact: the
exact release checkpoint does not exist before GPU training, and the generated-real
ABX must exercise that exact candidate rather than a synthetic teacher or placeholder.
Do not substitute clean-room teacher WAVs for the generated side.

Distribute **only** `public/`. Keep `private/answer_key.json` inaccessible to
listeners until responses are locked. Give each listener a separate copy of
`public/responses.csv`; they should use one stable `listener_id` on every row.
If `listener_id` is left blank, the v20 scorer derives it from the response filename.

Collect completed CSV files in one directory and score all listeners together:

```bash
python training/scripts/score_abx_v20.py \
  --key evidence/generated_real_abx_packet/private/answer_key.json \
  --responses evidence/generated_real_abx_responses \
  --out evidence/generated_real_abx.json
```

The v20 scorer accepts both new `answers` keys and legacy
`trials/generated_side` keys, and accepts `answer`, `guess`, or historical
`pick_generated` response columns. Release defaults still require at least five
accepted listeners and 60 target trials in total.

## 5. Read-only preflight before mutation

Once listener ABX has passed, run the exact-file preflight. This validates the
training provenance, curriculum, exact phrase fine-tune index, exact held-out
transition index, both promotions, and both **pre-seal checkpoint files**.

```bash
python training/scripts/run_schema8_post_gpu.py \
  --plan schema8_release_plan.local.json \
  --phase preflight
```

Do not continue if this fails.

## 6. Seal, manifest, commercial gate

```bash
python training/scripts/run_schema8_post_gpu.py \
  --plan schema8_release_plan.local.json \
  --phase seal

python training/scripts/run_schema8_post_gpu.py \
  --plan schema8_release_plan.local.json \
  --phase manifest

python training/scripts/run_schema8_post_gpu.py \
  --plan schema8_release_plan.local.json \
  --phase gate
```

`--phase seal` automatically runs the read-only preflight first. Sealing mutates
checkpoint metadata while verifying model/EMA/decoder tensor bytes do not change.
Because promotion evidence binds the pre-seal checkpoint file hash, do not treat
sealing as an idempotent command to rerun blindly on an already sealed file.

When every prerequisite already exists, the complete deterministic path can be run
as one command:

```bash
python training/scripts/run_schema8_post_gpu.py \
  --plan schema8_release_plan.local.json \
  --phase all
```

Use `--dry-run` first to print every command without executing it.

## 7. What is already complete vs still artifact-dependent

The **non-GPU implementation work is complete**: corpus/control tooling, provenance,
Schema 8 policy, transition evaluation/promotion, ABX preparation/validation/scoring,
status reporting, preflight, sealing, manifest construction, commercial gating,
production orchestration, documentation, and dependency-light CI are all present.

What cannot be manufactured before the trained model exists is production evidence:

1. the actual HQ and Compact/Frontier candidate checkpoints from GPU training;
2. candidate audio rendered from those exact trained checkpoints against rights-cleared held-out real material;
3. transition-evaluation/promotion reports computed against those real candidates;
4. independent human listening responses for generated-vs-real ABX; and
5. the final seals/manifest, which deliberately bind the exact resulting files.

Items 3 and 5 are automated once the trained checkpoints exist. Item 2 necessarily
runs the trained model, and item 4 necessarily requires human listeners. Everything
after those inputs is deterministic and fail-closed through the shared release plan.
