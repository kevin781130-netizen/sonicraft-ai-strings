# GPU training pause / resume

SONICRAFT renderer training supports safe pause/resume so a long GPU run does not
need to be hard-killed when the machine must be reclaimed, shut down, or restarted.

## Canonical trainer

For production renderer training, use the pausable entrypoint:

```bash
python training/train_ballad_renderer_pausable.py <the same renderer training arguments>
```

On Windows, the preferred entrypoint is the root launcher:

```bat
TRAIN_RENDERER_GPU.bat <the same renderer training arguments>
```

The launcher always invokes the pausable trainer and opens the local Training
Control Panel automatically. The original `training/train_ballad_renderer.py` remains
the shared renderer core imported by the pausable layer; do not use it as the
production GPU command.

Keep `--out` (last checkpoint) and `--best-out` (best validation/training score)
as different paths so the best candidate is not overwritten by a later, worse
epoch. For example:

```bat
TRAIN_RENDERER_GPU.bat --index datasets\processed\phrase_finetune\index.jsonl --preset hq_strings_v18 --epochs 100 --out Models\ballad_renderer_hq_v20_last.pt --best-out Models\ballad_renderer_hq_v20_best.pt
```

The pausable layer preserves the existing renderer dataset/model/loss contract and
adds only training-control/checkpoint behavior.

## Windows controls

Three root-level helpers are provided:

- `TRAINING_CONTROL_PANEL.bat` opens the localhost training-control page.
- `PAUSE_TRAINING.bat` requests a safe pause immediately without opening a browser.
- `RESUME_TRAINING.bat` restarts the most recently paused job from its saved checkpoint.

The control page is local-only and exposes status, PAUSE, and RESUME controls.

## What PAUSE means

PAUSE is cooperative, not a process kill. A pause request may arrive from the
control page, `PAUSE_TRAINING.bat`, Ctrl+C, SIGINT, or SIGTERM. The trainer records
the request and waits for the next complete optimizer boundary. It then writes a
resumable checkpoint and exits normally.

The pause checkpoint contains at least:

- model and EMA weights;
- optimizer and scheduler state;
- completed epoch / batch metadata and global optimizer step;
- Python, NumPy, CPU Torch, and CUDA RNG state when CUDA is active;
- codec geometry, preset, data-source mix, phrase provenance, and acoustic-promotion binding;
- a pause-state record explaining why and where the run stopped.

Do not power off the machine until status is `paused` or the console prints
`[PAUSED] checkpoint saved:`.

## Resume behavior

Resume uses the exact checkpoint recorded in `training/.training_status.json` and
reconstructs the original command with `--resume <checkpoint>`.

The control layer atomically switches status to `resuming` before it launches the
child process, so a rapid double-click on RESUME cannot start two copies of the same
training job while the child is still initializing.

If the pause happened between epochs, the next epoch starts normally. If it happened
mid-epoch, model/EMA/optimizer/scheduler/RNG progress is preserved, but that partial
epoch is replayed from its beginning with a fresh weighted-sampler order. Already
committed optimizer steps are not rolled back.

This is deliberate: it keeps checkpoints safe at optimizer boundaries without
serializing DataLoader internals or half-accumulated gradients.

## Files that are local runtime state

The following control files are runtime state and are ignored by Git:

- `training/.pause_training`
- `training/.training_status.json`

They may be deleted only when no training process is using them. Normally the
control scripts manage them automatically.

## CLI controls

Equivalent command-line controls are available:

```bash
python training/training_control.py status
python training/training_control.py pause
python training/training_control.py resume
python training/training_control.py clear
```

`clear` only removes a pending pause request; it does not resume a paused process.
Use `resume` for that.

## Failure boundary

A cooperative PAUSE protects against ordinary user-requested stops and handled
SIGINT/SIGTERM. It cannot guarantee a final checkpoint after an abrupt power loss,
GPU reset, kernel crash, out-of-memory kill, or OS-level forced termination. Keep the
normal epoch checkpoints on persistent storage as the fallback for those cases.
