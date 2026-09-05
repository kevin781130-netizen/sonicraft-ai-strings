# v1.9 Source Scout — Sound-data frontier

Date: 2026-08-31.

The v1.9 scout did not find a generic permissive backbone whose inclusion justified increasing the shipping surface. The remaining high-leverage open-source work is concentrated at the codec/evaluation boundary, so this release reuses the already-pinned permissive references rather than adding another framework.

## Revalidated

### ACE-Step 1.5

- MIT source repository.
- Current observed upstream head on 2026-08-31: `ca1e85fe9430179831e6bc6be790c332190a3866`, already exactly pinned in the project lock.
- Public implementation uses 48 kHz audio and 64-dimensional Oobleck VAE latents at 25 Hz; tiled VAE encoding is implemented upstream.
- Useful to SONICRAFT: codec geometry/tiled engineering and an external 25 Hz reconstruction challenger.
- Not imported: generic model weights as final SONICRAFT string timbre authority.

### ACE-Step VST3 / neural-codec

- MIT native C++/GGML engineering reference.
- Current observed upstream head: `b04bf8aec9be3bdd220050a0cc1c68d045b3b798`, already pinned.
- Demonstrates 48 kHz / 64-d / 25 Hz Oobleck encode+decode and compact latent quantization.
- v1.9 uses it only as a benchmark/native-runtime reference; no code or weight copy is necessary for the Sound Forge core.

## Decision

No 21st generic dependency is promoted. v1.9 invests the complexity budget in deterministic dataset intake, held-out codec tournament, blind listening evidence and release-integrity enforcement. This adds development capability while leaving the consumer neural core unchanged.
