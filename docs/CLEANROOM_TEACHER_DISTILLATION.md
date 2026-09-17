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

### Known Synthesizer V restriction

As of 2026-09-17, Dreamtonics' published usage terms for Dreamtonics-produced
Synthesizer V voice databases explicitly prohibit training machine-learning systems
using audio generated from the voice. Partner-produced voice databases may have
different terms and must be checked individually.

Official terms summary: https://dreamtonics.com/terms/

Therefore a Synthesizer V/Dreamtonics teacher must remain blocked in this pipeline
unless you have separate explicit written permission that grants the required
training use. Clean-room implementation does not override a license restriction.
The adapter requires a recorded evidence reference, and a Dreamtonics/Synthesizer V
provider additionally requires an explicit written-permission reference before it
will render teacher training data.

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

## 2. Generate multi-note phrase supervision

The phrase corpus extends the same independent physical teacher into deterministic
multi-note training examples. It currently balances six phrase families across all
four string instruments:

- legato scale fragments;
- portamento pairs;
- spiccato patterns;
- tremolo sustains;
- expressive dynamic arcs; and
- mixed-bowing phrases.

Each phrase writes WAV, MIDI, event JSON and a 100-Hz `control_curves` NPZ sidecar.
The sidecar contains per-frame pitch, gate, onset, articulation, legato, pitch bend,
dynamics, vibrato, transition and timing controls, so the renderer sees the actual
transition trajectory rather than one scalar label for the whole clip.

```bash
python training/scripts/generate_cleanroom_phrase_corpus.py \
  --out datasets/generated/cleanroom_phrases_v1 \
  --count 2400 \
  --seconds 2.0 \
  --seed 20260917
```

Smoke test:

```bash
cd training
python smoke_cleanroom_phrase.py
```

Both `encode_dac_latents.py` and `encode_vae64_latents.py` consume the optional
`control_curves` sidecar. Legacy rows without a sidecar retain their previous scalar
behavior. Phrase rows preserve `articulation_curve` in the latent NPZ, which is
already consumed by the renderer dataset/training path.

For VAE64, for example:

```bash
python training/scripts/encode_vae64_latents.py \
  --index datasets/generated/cleanroom_phrases_v1/index.jsonl \
  --codec checkpoints/strings_vae64.pt \
  --out datasets/processed/cleanroom_phrases_vae64 \
  --seconds 2.0
```

The phrase corpus remains `training_origin="modeled"` and
`final_timbre_anchor=false`; the origin-aware sampler remains responsible for
keeping modeled supervision within the intended mixture budget.

## 3. Phrase fine-tune and transition promotion

Build a combined latent index with phrase weighting applied only inside the MODELED
lane:

```bash
python training/scripts/build_phrase_finetune_index.py \
  --base-index datasets/processed/ballad_vae64/index.jsonl \
  --phrase-index datasets/processed/cleanroom_phrases_vae64/index.jsonl \
  --out datasets/processed/phrase_finetune/index.jsonl \
  --report datasets/processed/phrase_finetune/curriculum_report.json
```

The curriculum report records the exact combined index as `output_index_sha256`.
Renderer training derives a tamper-evident `phrase_finetune_provenance` marker from
the actual index rows, not from a user-provided release flag. The marker declares
`required_release_schema=8`, preserves the root phrase-index SHA-256, and is inherited
through resume, ordinary distillation, reflow distillation, and shortcut training.

Schema 8 also requires an independent training-provenance attestation. Stamp the
existing `training_provenance.json` from the exact curriculum report before building
the release manifest:

```bash
python training/scripts/stamp_phrase_training_provenance.py \
  --provenance evidence/training_provenance.json \
  --curriculum-report datasets/processed/phrase_finetune/curriculum_report.json
```

The resulting `phrase_supervision` record binds the same `output_index_sha256` to
the exact curriculum-report SHA-256 and declares `required_release_schema=8`. This
record is separate from checkpoint metadata, so release validation has two sources
of phrase lineage rather than trusting a single artifact.

After fine-tuning, evaluate baseline and candidate renderer checkpoints on the same
held-out phrase latent index with `evaluate_renderer_transitions.py`, then build a
`transition_promotion_v1` report with `build_transition_promotion.py`.

Seal HQ and Compact/Frontier only after each transition promotion passes. The sealer
rejects failed/underpowered promotion evidence and also checks that checkpoint
`phrase_finetune_provenance.phrase_source_index_sha256` equals curriculum
`output_index_sha256` before it writes any transition seal.

A passed phrase-fine-tuned release is a **Release Schema 8** build. Both shipping
renderer roles require their own checkpoint-specific transition promotion and
transition seal, and both must use the same held-out phrase index. Training
provenance, curriculum evidence, HQ lineage, and Compact lineage must all identify
the exact same fine-tune index. The codec decoder is not transition-sealed.

Both the manifest builder and commercial release gate reopen the staged training
provenance plus renderer checkpoints. If either source declares phrase supervision,
Schema 7 or older is rejected even if checkpoint markers or the manifest are edited.
The hash/attestation scheme is a tamper-evident consistency mechanism rather than a
digital signature; it does not claim authenticity against coordinated rewriting of
all unsigned artifacts.

See `docs/SCHEMA8_TRANSITION_RELEASE.md` for the exact seal, manifest-builder,
commercial-release-gate, and dependency-light smoke commands. Schema 8 does not
weaken or replace the existing Schema 7 acoustic promotion requirements.

## 4. Connect an authorized black-box teacher

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
after review, and `rights.evidence_reference` must document the basis for that
permission. Release training stays blocked unless the two additional release
rights flags are also true. For Dreamtonics/Synthesizer V, the adapter also requires
`rights.explicit_written_permission_reference` because the published standard voice
terms prohibit ML training on generated audio.

Example:

```bash
python training/build_cleanroom_teacher_dataset.py \
  --teacher-config D:/private/teacher_A.json \
  --out datasets/cleanroom_teacher_A \
  --count 4096 \
  --seed 20260917
```

Keep the config outside Git if it contains local/private paths.

## 5. Provenance and filtering

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

## 6. Registry gate

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

## 7. Existing Ai Strings path

Reuse the project's existing Sound Forge, deterministic segmentation, codec/latent,
renderer training and distillation pipeline. The clean-room path only adds permitted
behavioral supervision and phrase/transition evidence; it does not import private
teacher parameters or alter the runtime provenance boundary.

For external-teacher data, keep `training_origin="modeled"` and
`final_timbre_anchor=false`; the external teacher should supplement behavioral
coverage rather than silently replace the real-acoustic lane.
