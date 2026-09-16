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

Both `encode_dac_latents.py` and `encode_vae64_latents.py` now consume the optional
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
`final_timbre_anchor=false`; the existing origin-aware sampler is still responsible
for keeping modeled supervision within the intended mixture budget.

## 3. Connect an authorized black-box teacher

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

## 4. Provenance and filtering

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

## 5. Registry gate

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

## 6. Existing Ai Strings path

The builder intentionally stops at WAV + manifest. Reuse the project's existing
pipeline for Sound Forge, deterministic segmentation, codec/latent conversion,
renderer training and distillation. This keeps the v6.2+ performance/checkpoint
core unchanged and preserves the current provenance model.

For external-teacher data, keep `training_origin="modeled"` and
`final_timbre_anchor=false`; the external teacher should supplement behavioral
coverage rather than silently replace the real-acoustic lane.

## 7. Phrase fine-tuning and transition promotion

Phrase supervision is intentionally weighted **inside** the modeled lane. It never
raises the global modeled probability above the renderer's configured REAL80/MODEL20
policy. Build an audited fine-tune index after encoding phrase latents:

```bash
python training/scripts/build_phrase_finetune_index.py \
  --base-index datasets/processed/ballad_vae64/index.jsonl \
  --phrase-index datasets/processed/cleanroom_phrases_vae64/index.jsonl \
  --out datasets/processed/phrase_finetune/index.jsonl \
  --report datasets/processed/phrase_finetune/curriculum_report.json \
  --phrase-modeled-share 0.65
```

The curriculum report audits sampling at training progress 0.0, 0.5 and 1.0. The
MODELED lane must remain approximately 20% at every stage; `phrase-modeled-share`
only allocates probability *within* that lane.

Train the renderer with the merged index using the normal trainer. Keep a held-out
phrase latent index completely separate from the fine-tune index. Evaluate the
pre-fine-tune baseline and candidate with the same held-out index and seed:

```bash
python training/scripts/evaluate_renderer_transitions.py \
  --checkpoint checkpoints/baseline.pt \
  --index datasets/processed/cleanroom_phrases_heldout_vae64/index.jsonl \
  --out evidence/transition_baseline.json

python training/scripts/evaluate_renderer_transitions.py \
  --checkpoint checkpoints/phrase_candidate.pt \
  --index datasets/processed/cleanroom_phrases_heldout_vae64/index.jsonl \
  --out evidence/transition_candidate.json
```

Build the transition promotion report:

```bash
python training/scripts/build_transition_promotion.py \
  --baseline evidence/transition_baseline.json \
  --candidate evidence/transition_candidate.json \
  --curriculum datasets/processed/phrase_finetune/curriculum_report.json \
  --out evidence/transition_promotion.json
```

The default gate requires paired index/seed identity, at least 48 held-out phrase
samples, improved continuity, bounded acceleration/flow regression and a passing
composite ratio. A failed report exits non-zero.

Once the report passes, bind it to the exact candidate checkpoint without changing
model tensors:

```bash
python training/scripts/seal_transition_promotion.py \
  --checkpoint checkpoints/phrase_candidate.pt \
  --promotion evidence/transition_promotion.json \
  --curriculum datasets/processed/phrase_finetune/curriculum_report.json
```

The seal verifies the candidate file SHA-256 from the evaluation report and checks
the tensor digest before/after metadata binding. This transition seal is additional
evidence; it does not bypass the existing acoustic promotion, source-policy or
commercial-release gates.

Dependency-light curriculum/promotion smoke test:

```bash
cd training
python smoke_phrase_promotion.py
```
