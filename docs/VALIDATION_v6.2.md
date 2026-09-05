# SONICRAFT v6.2 Validation — Acoustic Runtime Provenance / Model Environment Binding

Validated 2026-09-03 in the available Linux source/build environment.

## Source/runtime validation

- v6.2 modules compile with Python bytecode compiler.
- Checkpoint capture/verify/replay/tamper/restore regression: PASS.
- Actual model byte SHA is bound and checked against declared manifest SHA: PASS.
- Cross-directory identical model bytes produce the same acoustic binding and Checkpoint ID: PASS.
- 48 kHz -> 44.1 kHz deliberate runtime drift is detected specifically as render configuration drift: PASS.
- Compiler replay remains PASS when only acoustic runtime configuration drifts: PASS.
- in-toto Statement / SLSA provenance-shaped local export contract: PASS.
- v6.2 Auto-Loop Checkpoint integration fixture: PASS.
- native v6.2 provenance contract build/smoke: see final build validation in `release/frontier_status_v6.2.json`.

## Release truth boundary

This validation does not claim a rebuilt v6.2 VST3, Steinberg Validator result, Cubase/Studio One real-host result, Windows GPU acoustic QA, signed installer, or bit-identical Audio Replay.

The v6.2 guarantee is provenance/reproducibility of the decision and observed acoustic execution environment, not cross-platform floating-point identity of rendered audio.
