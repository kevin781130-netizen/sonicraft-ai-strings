# v0.5 validation

The development package was checked with a synthetic commercial-safe manifest and fixed-shape latent/control segments.

Verified:
- source-policy validation accepts only registered commercial-safe sources;
- group-safe train/validation splitting runs;
- supervision-coverage audit runs;
- v0.5 23D continuous/control-validity path + time-varying articulation forward/backward runs;
- EMA training checkpoint and best-validation checkpoint are written;
- one CPU smoke epoch of the small test preset completes;
- one teacher->student distillation smoke epoch completes;
- Python modules compile after the smoke run.

The synthetic smoke checkpoints are deliberately **not** included in the release ZIP and are not audio-quality models.
