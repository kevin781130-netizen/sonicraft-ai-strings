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
