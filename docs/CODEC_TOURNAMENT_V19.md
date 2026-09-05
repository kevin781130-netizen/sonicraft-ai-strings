# SONICRAFT v1.9 Codec Tournament

The codec is now treated as an acoustic bottleneck, not a fixed dependency. v1.9 provides a codec-agnostic reconstruction tournament so SONICRAFT VAE64, DAC, ACE-Step/Oobleck or future legally usable challengers can be compared on the **same held-out real string clips**.

## Promotion order

1. **Reconstruction quality first.** Objective score is built from multi-resolution spectral error, log-spectrum error, SI-SDR, envelope correlation, transient flux and octave-ish band-energy error.
2. Modeled/clean-room clips are diagnostic only. They cannot choose the timbre codec winner.
3. Only candidates inside a narrow quality tie window (default 0.5 score point) may be ranked by latent state density and then decoder bytes.
4. Objective victory is insufficient. The selected codec must also pass blind codec ABX.
5. Generated-vs-real blind validation remains a separate release gate.

This ordering prevents a smaller 25 Hz codec from replacing a better-sounding 30 Hz codec merely because it is smaller.

## Current challenger geometry

The existing release codec is SONICRAFT-owned VAE64: 48 kHz mono string waveform, 64 latent channels at 30 Hz (1600x reduction).

ACE-Step 1.5 remains an external challenger/reference. Its public MIT code uses an Oobleck-style 48 kHz VAE with 64-dimensional latents at 25 Hz (1920x reduction). The separate MIT `acestep.vst3` project demonstrates native GGML codec encode/decode and Q8/Q4 latent storage. v1.9 does **not** import generic ACE-Step audio weights into the SONICRAFT release; a challenger must be evaluated/retrained under the SONICRAFT data and provenance rules before promotion.

Pinned source commits already present in the v1.8/v1.9 permissive source lock were rechecked on 2026-08-31:

- `ace-step/ACE-Step-1.5` — `ca1e85fe9430179831e6bc6be790c332190a3866` (latest commit observed; MIT source).
- `ace-step/acestep.vst3` — `b04bf8aec9be3bdd220050a0cc1c68d045b3b798` (latest commit observed; MIT source).

## Workflow

```text
scripts\PREP_CODEC_TOURNAMENT_V19.bat
```

This exports a deterministic held-out real-string reference set, reconstructs it through the local VAE64 checkpoint, and creates the first candidate-pair rows.

Round-trip the exact same numbered references through each external legal challenger, then append it:

```text
python training\scripts\build_codec_pairs_from_dir.py ... --append
```

Run objective tournament:

```text
scripts\RUN_CODEC_TOURNAMENT_V19.bat
```

Build blind A/B/X listening material:

```text
scripts\BUILD_CODEC_ABX_V19.bat
```

After collecting `listener_id,trial_id,answer`, score it with `training/scripts/score_codec_abx.py`. Schema 6 requires >=3 listeners, >=20 completed responses, and identification accuracy <= the declared target (default 0.60).

Objective metrics are engineering filters, not proof of perceptual transparency. Blind listening is the final codec promotion authority.
