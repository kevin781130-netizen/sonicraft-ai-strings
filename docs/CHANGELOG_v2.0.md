# SONICRAFT AI Strings Q4 v2.0 — Changelog

## Added

- Deterministic rights-preserving acoustic phrase segmentation for codec/evaluation anchors.
- Stereo/phase/harmonic string-specific codec tournament (`codec_tournament_v20.py`).
- Listener-QA and significance-aware ABX scorer (`blind_abx_v20.py`).
- Winner-take-all acoustic promotion contract (`acoustic_promotion.py`).
- v2.0 candidate curriculum token and promotion binding.
- Post-ABX tensor-preserving checkpoint seal.
- Schema-7 release integrity and evidence staging.
- v2.0 candidate-training, tournament, promotion, seal and release entrypoints.
- APCodec Reborn as a pinned MIT reconstruction challenger.

## Changed

- Codec ranking is quality-first. Footprint/latency only break perceptual near-ties.
- Stereo information is no longer collapsed before codec evaluation.
- Codec transparency and generated-vs-real perceptual gates are separate.
- v2.0 requires at least five valid listeners and at least sixty target ABX trials per perceptual report, plus listener QA/statistical guards.
- `build_release_model_manifest.py` supports Schema 7 while retaining Schema 6 as its default for backward-safe external callers; v2.0 scripts explicitly request Schema 7.

## Preserved

- REAL80/MODEL20 acoustic authority.
- Strict MIDI Authority.
- v1.8/v1.9 model-size target: 2,606,296 renderer + 1,281,137 decoder parameters.
- Schema 5/6 verification for older Model Packs.
- Consumer runtime remains free of Sound Forge/ABX/tournament neural dependencies.
