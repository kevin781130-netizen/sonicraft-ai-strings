# v0.4

- Added phrase-aware internal controls (16-dim conditioning total) while keeping the user MIDI map unchanged.
- Added fail-closed source policy validation to renderer training.
- Added CC-BY Ghent professional violin avatar audio/motion ingestion.
- Added Sanidha clean-stem importer and access-request template.
- Added audited MusicNet manifest builder and runtime-reverified Wikimedia PD/CC0 quartet reference downloader.
- Added a small realism critic for ensemble/room reference training.
- Added staged commercial training curriculum.
- Explicitly blocked VIOLET CSV-TD/checkpoints from commercial weights until dataset/checkpoint rights are clear; architecture remains a permitted clean-room reference.

## Training correctness fixes
- Normalized `dataset` / `dataset_id` and `audio` / `path` manifest schemas so the commercial gate cannot silently miss a source ID.
- Good-sounds 2025 manifests now emit the same canonical schema as Iowa/TinySOL.
- `scale-good` recordings are retained for codec/performance acoustics but are excluded from isolated-note MIDI conditioning unless true note alignment exists.
- Removed invented CC3 supervision from isolated public audio. Unknown vibrato, expression and pitch-bend labels now carry explicit internal validity masks.
- Renderer conditioning expands from 16 user/AI values to **21 internal dimensions** (16 values + 5 validity flags). The VST MIDI surface is unchanged.
- Added `CONTINUE_TRAIN_V04.bat`: commercial-safe staged codec + compact renderer + HQ renderer path; optional Good-sounds/Ghent/Sanidha sources are auto-detected.
- Deprecated the old URMP commercial-looking training entrypoint and renamed it research-only.
