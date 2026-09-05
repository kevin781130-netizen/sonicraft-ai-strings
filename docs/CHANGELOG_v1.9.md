# Changelog v1.9 — Sound Forge

- Added fail-closed Sound Forge dataset intake with registry rights gate, SHA-256, duplicate removal and conservative acoustic-quality diagnostics.
- Forge quality now influences only lane-internal curriculum weighting; REAL80/MODEL20 remains exact.
- Added parameter-free modeled-lane latent/physics geometry alignment; zero runtime parameters.
- Added codec-agnostic held-out reconstruction tournament with quality-first / compactness-second promotion logic.
- Added deterministic codec evaluation-set preparation and local VAE64 round-trip tool.
- Added blind A/B/X codec trial builder and exact-binomial scorer.
- Added schema-6 release evidence: Sound Forge + codec tournament + codec ABX, in addition to provenance/model hashes and generated-vs-real ABX.
- Added schema-6 hash verification in runtime and commercial release gate.
- Added v1.9 Standard/Full-HQ model-pack evidence propagation.
- Added `TRAIN_STRINGS_SOUND_FORGE_V19.bat`, codec tournament entry points and v1.9 regression smoke.
- No consumer model parameters were added by Sound Forge, codec tournament or physics-metric regularization.
