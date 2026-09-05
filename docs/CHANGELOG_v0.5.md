# SONICRAFT AI Strings Q4 v0.5

## Training quality changes
- Added EMA weights for rectified-flow training; release/evaluation should prefer EMA.
- Added group-safe train/validation split to prevent adjacent clips from the same piece/session leaking into validation.
- Added best-checkpoint selection instead of assuming the last epoch is the best.
- Added cosine LR schedule, gradient accumulation, bf16 autocast on supported CUDA GPUs, resume of optimizer/scheduler/EMA.
- Added note-aware flow loss: attack/onset and connected-legato regions receive extra weight; added first- and second-order latent continuity losses.
- Added classifier-free-style dropout only for optional expressive controls. Pitch, gate and onset are never dropped.
- Added time-varying articulation curve support so a single phrase may switch articulations; user still sees the same 12 keyswitches.
- Added internal `bow_change_prob` and `vibrato_onset` features. They do not add new CC lanes.
- Added supervision coverage report for CC1/CC3/CC11/legato/pitchbend/articulation.

## Runtime direction
The VST workflow remains LASS/Chris-Hein familiar: notes + keyswitches + CC1/CC3/CC11 remain authoritative. v0.5 only improves what the AI learns behind that interface.

## Teacher -> student
HQ is now explicitly the realism teacher. After HQ convergence, the compact renderer is distilled from the HQ EMA checkpoint. This is the preferred path to keep the realtime/local footprint small without training the small model in isolation.

## Commercial safety
No change to the fail-closed source gate. Research-only or unclear-rights datasets remain excluded from release training.
