# v0.8 validation report

Validation performed in the artifact environment:

- Python `compileall` over `training/`: PASS.
- v0.8 renderer forward/backward smoke: PASS.
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

## Additional v0.8 checks performed in artifact environment
- Python `compileall` over `training/`: PASS.
- 34D `BalladFlowRenderer` forward/backward: PASS.
- Real-audio offline analyzer on a synthetic 16-kHz A4 vibrato signal: PASS; detected/calibrated physical depth path and independent masks are present.
- Data-driven CC3 calibration fit + application over synthetic rights-cleared fixtures: PASS; anchors are monotonic and continuous.
- Per-output Vibrato Expert one optimizer epoch: PASS.
- Commercial source audit with an intentionally blocked NC source: FAIL-CLOSED as expected.
- `preview_engine.cpp` standalone `g++ -std=c++17 -Wall -Wextra -Werror`: PASS.

These tests prove engineering-path integrity, not final acoustic quality. Final release acceptance still requires CUDA training on the actual commercial-safe corpus and blind held-out real-performance ABX.
