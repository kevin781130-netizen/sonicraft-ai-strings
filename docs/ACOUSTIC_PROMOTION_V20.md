# SONICRAFT v2.0 Acoustic Promotion

## Purpose

v2.0 freezes the shipping neural architecture and makes acoustic promotion evidence-driven. A candidate is not a release merely because it trains, exports, or wins an objective metric. It must survive a fixed sequence of rights, reconstruction, perceptual and binding gates.

## Promotion sequence

1. **Sound Forge** admits only registry-cleared material and preserves the immutable REAL80/MODEL20 policy.
2. **Acoustic Segmentation** creates deterministic phrase-sized codec/evaluation anchors without rewriting renderer score/control timelines.
3. **Codec Tournament v2** compares held-out real-string reconstructions with stereo-aware spectral, transient, band-energy, phase-derivative, harmonic-texture, stereo-correlation and stereo-width metrics.
4. **Codec Transparency ABX** independently tests whether reconstruction damage remains identifiable.
5. **Generated-vs-Real ABX** independently tests the complete renderer. A transparent codec cannot hide a synthetic renderer.
6. **Acoustic Promotion** names exactly one shipping codec only if all gates pass and an audited runtime adapter exists.
7. **Promotion Seal** writes the promotion ID and a tensor digest into HQ, Frontier and decoder checkpoint metadata. The tensor digest must remain unchanged before/after sealing.
8. **Schema 7 Release** verifies evidence hashes, winner identity, checkpoint seals and REAL80/MODEL20 policy before Model Pack creation.

## Candidate vs released model

`CANDIDATE_V20` selects the v2.0 curriculum but deliberately carries no winner claim. Candidate checkpoints must never be distributed as promoted models. Only post-ABX sealed checkpoints are Schema-7 eligible.

## Acoustic authority

Real recordings remain the only final timbre/adversarial-real authority. Modeled clean-room audio remains 20% and is used for physics, rare-state, section-dispersion and latent-geometry supervision. It cannot become the acoustic realism target.

## Runtime cost

The v2.0 Sound Forge, segmentation, tournament, ABX scorer, promotion builder and seal are training/release tools. They add **zero neural parameters** to the consumer runtime. The current shared renderer remains 2,606,296 parameters and the VAE64 decoder 1,281,137 parameters: 3,887,433 total, approximately 7.41 MiB of raw FP16 weights.

## Promotion is not pre-claimed

Engineering smoke tests validate the machinery, not acoustic superiority. A production release is acoustically promoted only after rights-cleared real-string training and real blind-listening evidence satisfy the same Schema-7 gates.
