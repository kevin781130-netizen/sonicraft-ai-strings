# SONICRAFT AI Strings Q4 — v1.2 RC2 validation

Date: 2026-08-30

## Passed in the artifact environment

- Python `compileall` for `runtime/` and `training/`.
- C++20 `-Wall -Wextra -Werror` compile for `preview_engine.cpp` and `shadow_render_client.cpp`.
- VSTGUI UIDESC XML parse.
- Renderer-service mock IPC: first render returns audio; identical second request returns cache-hit.
- Release-integrity fail-closed behavior when model manifest is missing.
- Release model manifest + commercial release gate with a synthetic safe fixture.
- Release evidence integrity: modifying `release_metrics.json` after approval is rejected by SHA-256 verification.
- Required release roles: HQ renderer + strings DAC fine-tune + pinned DAC base; Compact is optional for AUTO acceleration.
- Runtime cache key includes the model fingerprint.
- No research-only/NC dataset can be enabled in the commercial registry gate.

The synthetic release fixture validates **release plumbing only**. It is never shipped as an acoustic model and is not evidence of audio quality.

## RC1 release acceptance rules

A public commercial build must have all of the following:

1. Rights-cleared immutable training provenance. Every source ID must exist in the commercial dataset registry and be non-blocked.
2. Approved model pack containing HQ renderer, strings-specialized DAC decoder fine-tune, and the exact Descript DAC 44.1kHz/16kbps base file. Every file is SHA-256 pinned.
3. Held-out control validation: MIDI lock, monotonic CC3 vibrato-depth response, tempo-aware transition behavior, and renderer-dropout LIVE fallback.
4. Blind held-out real-vs-generated listening test. RC1 gate requires at least 3 listeners and 20 completed trials, with generated-identification accuracy <= 0.60.
5. Windows x64 MSVC Release build of the VST3 and PASS from Steinberg's official VST3 validator.
6. Real Cubase host test: load/save/reload, tempo-map changes, sample-accurate CC1/CC3/CC11/CC20 automation, keyswitches, LIVE/AUTO/HQ, service restart, cache invalidation, and offline export.
7. Authenticode signing + timestamp of public EXE/VST3 payloads and signature verification.

## Important RC1 audio-thread changes

- VST3 parameter points are merged with MIDI events at their VST3 sample offsets rather than applying the last point to the entire block.
- At an identical sample offset, parameter automation is applied before note-on so an onset receives the intended CC state.
- No heap allocation was added to the VST3 `process()` path for automation collection; a fixed-capacity scratch array is used.
- AUTO/HQ CUDA work remains outside the audio callback.

## Remaining environment-dependent blockers

This Linux artifact environment cannot truthfully certify the final Windows/Cubase binary or create the final acoustic weights. The public `BUILD_COMMERCIAL_RELEASE.ps1` pipeline refuses release until the Windows validator and commercial model/ABX gates pass. A public build should also be signed with a trusted Windows code-signing identity; an unsigned build is RC/testing only.
