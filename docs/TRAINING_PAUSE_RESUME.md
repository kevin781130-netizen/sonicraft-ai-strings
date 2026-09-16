# GPU training pause / resume

SONICRAFT renderer training supports safe pause/resume so a long GPU run does not
need to be hard-killed when the machine must be reclaimed, shut down, or restarted.

## Canonical trainer

For production renderer training, use the pausable entrypoint:

```bash
python training/train_ballad_renderer_pausable.py <the same renderer training arguments>
```

It preserves the existing renderer dataset/model/loss contract and adds only the
training-control/checkpoint layer.

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
