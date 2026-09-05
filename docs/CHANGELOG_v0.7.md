# SONICRAFT AI Strings Q4 — v0.7 changelog

v0.7 moves the performance layer from fixed-millisecond heuristics toward **learned beat-domain performance timing** while keeping the user's MIDI surface compact and familiar.

## Performance timing

- Added `training/performance_timing.py`.
- Slow / Normal / Fast are no longer defined as one fixed number of milliseconds. They are represented as distribution targets in beat space and converted to milliseconds from the current host tempo at render time.
- Default fallback priors are intentionally conservative; `training/fit_timing_calibration.py` replaces them with 20th / 50th / 80th percentile calibration only when rights-cleared aligned transition data is available.
- Physical clamps prevent musically impossible transition durations at extreme tempi.
- Tempo automation remains a render condition rather than an edit to the user's MIDI notes.

## Four performance expert paths

The renderer now separates the most realism-critical behaviors instead of asking one generic transition module to solve all of them:

1. **Vibrato Expert** — CC3 depth request, natural rate, onset delay, micro-jitter and evolution.
2. **Legato Expert** — overlap, attack suppression, continuity and beat-normalized transition duration.
3. **Portamento Expert** — slide duration, extent, curve shape and arrival softness.
4. **Bow-change Expert** — rebow timing, transient strength, brightness change and continuity.

Legato, Portamento and Bow-change are strongly tempo-aware. Vibrato remains free-running: tempo may inform musical context but never hard-locks vibrato cycles to the metronome.

## Cubase / VST3 integration

- The controller now implements Steinberg `IKeyswitchController` and exposes the existing 12 C0–B0 articulation switches to compatible VST3 hosts.
- The articulation bank remains 12 patches. Speed is a separate modifier through optional CC20: Auto=0, Slow=42, Normal=84, Fast=127.
- This avoids multiplying 12 articulations into dozens of redundant Slow/Normal/Fast patches.
- `cubase/SONICRAFT_AI_Strings_v07_articulation_speed_recipe.csv` documents a compact Expression Map recipe.

## Training / commercial provenance

- Added commercial-gated physical-label derivation in `training/derive_performance_physics.py`.
- Added source-supervision masks for Legato / Portamento / Bow-change physics.
- Corrected a permissive-rights assumption for a Wikimedia vibrato example: the inspected file is ShareAlike/GFDL multi-licensed, so it is release-blocked pending explicit legal interpretation for learned weights.
- ARME / SPD / MUSC-style high-value research sources remain isolated from commercial checkpoints unless an explicit commercial ML/model-weight grant is verified.

## Training entry point

Run:

```bat
scripts\CONTINUE_TRAIN_V07.bat
```

The pipeline performs source gating, group-safe split, control coverage audit, beat-domain timing calibration, separate performance-expert training, HQ teacher training and HQ-to-Compact distillation.

No bundled smoke checkpoint is a release-quality model. Final realism still depends on rights-cleared professional Q4 recordings with aligned Legato, Portamento, Vibrato and Bow-change performances.
