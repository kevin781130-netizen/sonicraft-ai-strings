# SONICRAFT AI Strings Q4 v1.2 RC2 — Commercial release hardening

This release candidate adds a fail-closed commercial model gate. AUTO/HQ will only load a model package when `release_model_manifest.json` marks it approved and commercial-safe and every checkpoint SHA-256 matches. Research/unknown sources cannot be silently admitted into a public release.

## Public release gate
1. Build x64 VST3 with MSVC and static runtime.
2. Run the official Steinberg VST3 validator; absence of the validator is now a release failure.
3. Produce final HQ + optional Compact + DAC checkpoints.
4. Generate immutable training provenance and verify every used dataset against `dataset_registry.json`.
5. Run held-out MIDI-lock, vibrato-depth monotonicity, tempo-transition, service-dropout/fallback and blind ABX tests.
6. Build an approved model manifest containing hashes for models, provenance and metrics.
7. Build consumer Setup containing a prebuilt VST3; users must not need Visual Studio.
8. Authenticode-sign VST3 binary, renderer launcher, Manager and Setup with SHA-256 + timestamp.
9. Generate `release_hashes.json`.

## ABX release criterion
The supplied template uses <=60% generated/real identification accuracy as the upper release target, on held-out material with at least the listener/trial counts selected for the release study. It is deliberately not auto-passed from synthetic smoke tests.

## Still external to this Linux artifact environment
A public commercial build cannot be truthfully certified until the Windows/MSVC validator run, signed binaries, final rights-cleared model weights and held-out ABX result exist. `BUILD_COMMERCIAL_RELEASE.ps1` now enforces these rather than packaging an incomplete build as final.

## Packaging policy
Public release is split into a small Core Setup and a separate verified Model Pack. CUDA/PyTorch remains an optional runtime download. This keeps the plug-in core small and lets model updates invalidate cache via a model fingerprint without replacing the VST3 binary.

The public Model Pack also requires the upstream MIT-licensed Descript `weights_44khz_16kbps.pth` as the `dac_base` role. This removes first-render network downloading and makes the acoustic model package reproducible/offline once the optional Python/CUDA runtime is installed.
