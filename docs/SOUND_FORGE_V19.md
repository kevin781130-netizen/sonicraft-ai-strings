# SONICRAFT v1.9 Sound Forge

v1.9 moves the acoustic bottleneck from network architecture to **what is allowed to teach the network and how strongly it is trusted**. It adds no consumer inference parameters.

## 1. Fail-closed intake

`training/sound_forge.py` and `training/scripts/build_sound_forge_manifest.py` turn ordinary JSONL audio manifests into a hashed, graded training manifest.

Commercial eligibility is **never inferred** from a filename, URL or a license-looking string inside a row. The dataset ID must exist in `training/dataset_registry.json` and the audited registry entry must be enabled, `commercial_safe=true`, and `release_blocked=false`. A row-level block always wins.

Every admitted audio item can carry:

- SHA-256 audio hash;
- sample rate, channel count and duration;
- peak/RMS/crest/DC diagnostics;
- clipping and near-silence ratios;
- a conservative frame-dynamic/SNR proxy;
- sub-40 Hz and >18 kHz energy diagnostics;
- `forge_quality_score`, quality tier and reject reasons.

Exact duplicate audio is removed from training admission. Technical quality rejection does **not** rewrite source rights; rights and audio-quality decisions remain separate in the report.

## 2. REAL80 / MODEL20 remains absolute

Sound Forge is a filter/ranker *inside* each source lane. It does not choose the global lane ratio. `training/string_source_mixer.py` still normalizes training probability to exactly:

- 0.80 rights-cleared real acoustic strings;
- 0.20 independently modeled clean-room bowed-string physics.

The v1.9 curriculum is `lane_locked_quality_coverage_forge_v19`. Early epochs preserve rare instrument/articulation coverage; later epochs trust high-quality real recordings more strongly. Forge quality can redistribute probability only within a lane.

Modeled data remains forbidden as final timbre/adversarial-real authority.

## 3. Physics geometry without runtime growth

The v1.8 training-only `StringPhysicsProbe` remains. v1.9 adds `training/physics_latent_alignment.py`, a **parameter-free** pairwise geometry regularizer. When multiple modeled examples share enough exact physics labels, relative physical distance is aligned with relative latent distance.

This can teach continuity across bow speed, bow force, contact point, vibrato and section dispersion without adding a runtime network and without comparing modeled timbre to real timbre. Default weight is deliberately small (`0.03`) and remains ABX-gated.

## 4. Main training entry

Run on the CUDA training machine:

```text
scripts\TRAIN_STRINGS_SOUND_FORGE_V19.bat
```

It builds one audited Forge universe covering all audio allowed to influence the v1.9 acoustic weights, trains the VAE64, forges the renderer-control subset, preserves Forge quality metadata into latent indexes, then trains HQ -> Frontier distillation -> Shortcut specialization.

The script does **not** claim an acoustic release at completion. Codec tournament and both blind listening gates still have to pass.
