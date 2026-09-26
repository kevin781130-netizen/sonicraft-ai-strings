# Four DNNI Timbres — Research Integration

This branch keeps four user-supplied DNNI packages as **four separate timbre references** while preserving the existing SONICRAFT commercial clean-room gate.

## What was verified

All four supplied packages use the same DNNI v4 container skeleton: 140-byte header, four declared sections, and a 132,502,456-byte section-2 payload. The four section-2 SHA-256 values differ, so the packages are distinct. No reliable public tensor-name/shape map for this DNNI format is assumed by this integration.

`weights_fp16.bin` is therefore **not** loaded as a PyTorch `state_dict`. Treating a flat proprietary payload as if it matched SONICRAFT layer order would silently corrupt training.

## Local import (source binaries remain out of Git)

```bat
python training\scripts\import_dnni_four_timbres.py ^
  --source D:\dnni\one.tar ^
  --source D:\dnni\two.tar ^
  --source D:\dnni\three.tar ^
  --source D:\dnni\four.tar ^
  --out datasets\dnni_four_timbres\source
```

The importer creates one directory per timbre and a `bundle_manifest.json` with source/weight SHA-256 and FP16 probes. `datasets/` is already ignored by Git.

## Capture the four timbres

Create the deterministic capture sheet:

```bat
python training\scripts\generate_dnni_capture_plan.py
```

Render each row using the corresponding DNNI timbre, 48 kHz WAV recommended, and save it exactly at the `expected_wav` path. Synthesizer V Studio 2 exposes WAV bounce/export in its Render panel; scripting can be used to automate project editing, but this repository does not assume a private/undocumented DNNI inference API.

Build the training manifest:

```bat
python training\scripts\build_dnni_render_manifest.py
```

## RTX 5090 research training

```bat
scripts\TRAIN_DNNI_FOUR_TIMBRES_5090_RESEARCH.bat
```

The chain trains a VAE64 acoustic codec, encodes the four capture lanes, trains the HQ renderer, distills to Frontier Core, then performs shortcut distillation.

## Release status

Every raw capture row is tagged `release_blocked=true`, `commercial_safe=false`, and `cleanroom_eligible=false`. The existing latent encoder does not preserve every release-policy flag, so the research wrapper additionally requires the immutable research identity markers `dataset=dnni_research_timbre_*` and `source_kind=proprietary_teacher_render_research_only` before it will bypass the **commercial training source check for that process only**. It does not alter the standard release/promotion gates and must not be used to claim a clean-room commercial checkpoint.

The manifest uses `training_origin=real` only to tell the existing research loss code that captured teacher audio is the acoustic target rather than the SONICRAFT physics-model lane. That label is a sampler/loss-control mechanism here; it is **not** a rights or provenance claim that the audio is a rights-cleared real-instrument recording.


## One-click train / safe stop / auto resume

From the repository root on Windows:

- Double-click `TRAIN_DNNI_5090.bat` to start the whole RTX 5090 pipeline.
- Double-click `STOP_DNNI_5090.bat` while training to request a safe stop after the current batch/optimizer step. A partial epoch checkpoint is saved and that epoch is replayed when training resumes.
- Double-click `TRAIN_DNNI_5090.bat` again later; existing VAE64, HQ renderer, distillation, and shortcut checkpoints are detected automatically and resumed.
- A direct Ctrl+C/window close still preserves the last completed epoch checkpoint, but the unfinished epoch may need to be repeated.

The main pipeline uses `SONICRAFT_STOP_FILE` only when launched by the DNNI BAT. Normal SONICRAFT commercial training commands are unaffected.


### Control panel and recovery

For normal use, double-click `DNNI_5090_MANAGER.bat`. It provides Start/Resume, Status, Safe Stop, and shortcuts to the checkpoint/data folders.

`STATUS_DNNI_5090.bat` reports capture rows, latent rows, and epoch progress for all four trainable stages. The main trainer runs the same checkpoint-health scan before auto-resume. If a checkpoint cannot be loaded or its expected identity is wrong, automatic resume is blocked instead of overwriting it.

Checkpoint writes for VAE64, HQ renderer, distillation and shortcut training are atomic: the new checkpoint is first written to a sibling `.tmp` file and replaces the previous `.pt` only after the write succeeds. This preserves the last complete checkpoint if Windows, Python, or the training process is interrupted during serialization. Safe-stop requests are checked inside the training loop after a batch/optimizer step; partial checkpoints record `partial_epoch` and `partial_batches`, while `epoch` remains the last fully completed epoch so resume never skips unfinished work.


## Windows 5090 control flow

For normal use, open `DNNI_5090_MANAGER.bat`:

1. **Setup / Repair RTX 5090 environment** runs `SETUP_DNNI_5090.bat`. The pinned Windows path is Python 3.11 + PyTorch 2.11.0 + TorchAudio 2.11.0 from the CUDA 13.0 wheel index, followed by an NVIDIA/PyTorch/BF16/disk preflight.
2. **Import / Verify four DNNI TAR files** expects the private, gitignored `dnni_input\` folder to contain exactly `01_*.tar`, `02_*.tar`, `03_*.tar`, `04_*.tar`. The order is deterministic and becomes `timbre_1` through `timbre_4`.
3. **Start / Resume training** runs the full stage chain with automatic checkpoint detection.
4. **Training status** displays source hashes, capture/latent row counts, completed epochs, and partial-epoch safe-stop state.
5. **Safe stop** requests a checkpoint after the current batch/optimizer step.
6-9 open checkpoint, dataset, log, and private input folders.

Per-stage console output is appended under `logs\dnni5090\`.

## DNNI timbre supervision vs articulation supervision

The four imported packages are treated as four distinct timbre/acoustic references. Generated capture-plan rows now default to `articulation_verified=false`. Corresponding manifests set `articulation_known=0` unless a capture has independently verified articulation semantics.

The renderer and runtime model also gate legato/portamento expert activation with `articulation_known`, and the renderer loss no longer applies portamento-specific weighting to unknown articulation labels. This prevents DNNI timbre captures from accidentally teaching fabricated string articulation behavior while leaving ordinary known-articulation runtime behavior unchanged.

## Synthesizer V Studio 2 export boundary

The documented SV2 scripting API can create/edit project data and tracks, and `Track.setBounced()` can mark whether a track is included in file export. The documented audio export itself remains a Render Panel / **Bounce to Files** operation. This integration therefore does not depend on an undocumented render CLI or private scripting call. Once WAV captures exist in the expected paths, manifest creation, latent encoding, training, resume, status, and recovery are automated.


## Four-bounce capture workflow

The manual export bottleneck is reduced to four long bounces:

1. Run `PREPARE_DNNI_CAPTURE.bat`.
2. The tool generates the regular capture plan plus four long MIDI files under `datasets/dnni_four_timbres/batch_capture/`.
3. In Synthesizer V Studio 2, import one MIDI per timbre and assign the matching installed voice/timbre.
4. Bounce exactly four long WAV files to:
   - `datasets/dnni_four_timbres/batch_bounces/timbre_1.wav`
   - `.../timbre_2.wav`
   - `.../timbre_3.wav`
   - `.../timbre_4.wav`
5. Run `SLICE_DNNI_BOUNCES.bat`, or simply run `TRAIN_DNNI_5090.bat`; the main trainer detects all four long bounces and slices them automatically.

The generated MIDI uses a 60 BPM deterministic timeline with lead/gap spacing. The slicer detects the first rendered onset and estimates a constant timeline offset, so export that trims or retains the initial silence can still be aligned before the individual capture WAVs are written.

Synthesizer V Studio 2 officially supports MIDI import and documents WAV export through the Render Panel / Bounce to Files. This workflow uses those documented paths and does not depend on a private render CLI:
- https://sv2.docs.dreamtonics.com/en/inst-plugin
- https://sv2.docs.dreamtonics.com/en/render

## Data fingerprint and stale-artifact protection

Before training, SONICRAFT computes a portable SHA-256 fingerprint over the semantic four-timbre configuration, imported DNNI source/weight hashes, capture plan, capture controls, and rendered-audio hashes. Absolute local drive paths and display-only timbre labels are excluded.

The fingerprint is stored in the VAE64, HQ renderer, Frontier distill, shortcut checkpoints, and latent provenance. A stale/missing fingerprint blocks automatic resume. This catches cases such as replacing one DNNI package, re-rendering a WAV, changing a model-relevant timbre ID/instrument ID/MIDI range, or mixing latents from an older dataset.

If a data change is intentional, use `RESET_DNNI_5090.bat` (or Manager option **Archive / Reset**). It moves old checkpoints/latents/logs into `archive/dnni5090/<timestamp>/` and never deletes the DNNI source packages or rendered WAVs.

Changing only the human-readable `label` in `training/configs/dnni_four_timbres.json` does not invalidate model artifacts.

## Four-timbre model geometry

The normal SONICRAFT string presets historically default to three instrument embeddings. The DNNI research lane uses dedicated `hq_dnni4` and `frontier_core_dnni4` presets with `instruments=4`, so timbre IDs 0, 1, 2 and 3 all have valid embeddings. The standard commercial presets are not changed.

Velocity from the generated MIDI is also marked unverified by default. Unless independently verified, the research manifest uses a neutral velocity/dynamics condition instead of teaching a possibly false MIDI-velocity-to-timbre relationship.
