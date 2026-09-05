# v0.7 validation report

Validation performed in the artifact environment:

- Python `compileall` over `training/`: PASS.
- v0.7 renderer forward/backward smoke: PASS.
- Neural control dimension count: 34.
- Vibrato Expert forward: PASS.
- Legato / Portamento / Bow-change expert forward/backward: PASS.
- CC3 depth anchor monotonicity: PASS.
- Slow < Normal < Fast vibrato-rate tendency: PASS.
- Slow > Normal > Fast transition duration for Legato/Portamento/Bow-change: PASS.
- Tempo adaptation: the same Normal Legato request produces a shorter millisecond transition at 96 BPM than at 56 BPM: PASS.
- Synthetic one-epoch timing calibration: PASS.
- Synthetic one-epoch Performance Expert optimizer/backward: PASS.
- Synthetic one-epoch Vibrato Expert optimizer/backward: PASS.
- Supervised Vibrato + Performance Expert checkpoints loaded into the exact HQ renderer submodules and one integrated renderer epoch completed: PASS.
- Per-output physics masks: transition timing can be supervised without implicitly fabricating overlap/attack/arrival-softness/bow-color labels: PASS (code-path validation).
- Standalone `preview_engine.cpp` strict compiler smoke (`-Wall -Wextra -Werror`): expected as a packaging gate and rerun before ZIP creation.

The synthetic fixtures verify training mechanics only. They are not acoustic training data and their checkpoints are not packaged as release weights.

## Not validated in this environment

A complete VST3 binary build requires the Steinberg VST3 SDK plus the Windows Visual Studio toolchain. A full CUDA HQ training run requires the actual rights-cleared recording corpora and NVIDIA runtime. Neither should be represented as completed by this validation report.
