# Clean-room teacher distillation

This path is for **behavioral interoperability and synthetic-data generation**, not
for extracting or reproducing a third-party model's private internals.

## Boundary

The clean-room side may create its own MIDI, performance controls, seeds, splits,
quality metrics and student architecture. An external teacher is treated as an
opaque, authorized renderer:

```
independently-authored MIDI + control JSON
        -> authorized renderer/runtime
        -> WAV
        -> quality gate + intra-run de-dup
        -> SONICRAFT manifests
        -> existing codec/segment/training pipeline
```

The adapter does **not** parse, decrypt, import, serialize, translate or commit
teacher weights. Do not place `.dnni` or other proprietary model files in Git.
A SHA-256 fingerprint can optionally be recorded for provenance without embedding
the file.

This architecture reduces provenance risk but does not make a blanket legal
determination. The external runtime/model license controls whether its rendered
outputs may be used for training and whether learned weights may be released or
commercialized.

## 1. Run the independent teacher first

No third-party model is needed:

```bash
python training/build_cleanroom_teacher_dataset.py \
  --out datasets/cleanroom_teacher_internal \
  --count 256 \
  --seed 20260917
```

This uses `training/cleanroom_bowed_synth.py`, which is the repository's independently
authored bowed-string physical teacher. Rows use the already registered
`synthetic_cleanroom_bowed_v18` source ID.

Smoke test:

```bash
cd training
python smoke_cleanroom_teacher.py
```

## 2. Connect an authorized black-box teacher

Copy `training/cleanroom_teacher_config.example.json` outside the repository and
edit it for a small shim around the runtime/API you are actually allowed to use.

The command is an argv array (never a shell string). Supported placeholders are:

- `{control_json}` - independently authored SONICRAFT controls
- `{midi}` - independently authored MIDI probe
- `{output}` - requested WAV output path
- `{model}` - external model path
- `{seed}` - deterministic probe seed

The shim must use the runtime through an authorized interface. It must not dump
weights, private tensors, encrypted sections, signatures or hidden metadata.

The config is fail-closed. External rendering will not start until both
`rights.authorized_runtime_use` and `rights.output_training_allowed` are set true
after review. Release training stays blocked unless the two additional release
rights flags are also true.

Example:

```bash
python training/build_cleanroom_teacher_dataset.py \
  --teacher-config D:/private/teacher_A.json \
  --out datasets/cleanroom_teacher_A \
  --count 4096 \
  --seed 20260917
```

Keep the config outside Git if it contains local/private paths.

## 3. Provenance and filtering

Each accepted row records:

- deterministic sample ID, split and seed;
- instrument/articulation and the original control/MIDI hashes;
- output WAV SHA-256;
- an intra-run coarse fingerprint for duplicate suppression;
- Sound Forge audio-quality metrics;
- the teacher alias/runtime fingerprint where available;
- whether the teacher rights declaration allows release training.

The coarse fingerprint is **only an intra-run duplicate detector**. It is not a
copyright detector and cannot prove that an output is free of memorized material.
For external teachers, add a separate held-out review and similarity/memorization
screen appropriate to the model before release.

## 4. Registry gate

External-teacher rows use the source ID `authorized_blackbox_synthetic`. The
repository intentionally ships only a fail-closed fragment:

`training/cleanroom_teacher_registry.fragment.json`

Do not mark it `commercial_safe` or remove `release_blocked` merely because the
data was generated synthetically. Merge/enable it only after preserving evidence
that the applicable teacher/runtime terms permit:

1. the runtime/model use you perform;
2. use of rendered outputs for ML training;
3. creation/release of learned weights; and
4. commercial use, if that is your intended release.

`training/source_policy.py` remains the final dataset gate, so an unknown or
blocked source cannot silently enter a release checkpoint.

## 5. Existing Ai Strings path

The builder intentionally stops at WAV + manifest. Reuse the project's existing
pipeline for Sound Forge, deterministic segmentation, codec/latent conversion,
renderer training and distillation. This keeps the v6.2+ performance/checkpoint
core unchanged and preserves the current provenance model.

For external-teacher data, keep `training_origin="modeled"` and
`final_timbre_anchor=false`; the external teacher should supplement behavioral
coverage rather than silently replace the real-acoustic lane.
