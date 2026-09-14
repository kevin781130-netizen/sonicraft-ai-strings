# SONICRAFT AI Strings v7.0 RC2 — Commercial Release Readiness

## Decision

The v7.0 RC2 source tree is treated as **software-side commercial-release ready** once `RC_SOURCE_GATE_V70` and the commercial-source CI pass. This does **not** approve a distributable commercial binary. Binary approval remains fail-closed and requires the external evidence already defined by `FINAL_GATE_V70` and `PUBLIC_RELEASE_GATE_V70`.

No new performance-engine or frontend features should be added before the v7.0 commercial release. Changes are limited to release hardening, compliance, packaging, reproducibility, validation harnesses, and fixes required by a failed gate.

## Product release scope and StringCC lineage

The product baseline remains the v7.0 RC2 source convergence at commit `4f9f1915d6179ffb3d669bbb3a483c4e30643fbf`.

StringCC governance bridge v1.1 was merged later at commit `5c2f16816d40edaba1e9dcbee7ce43467d0a8f27`. It is an **optional developer interoperability component**, not a performance-core replacement and not part of the consumer VST3/prebuilt payload. It stays under `integrations/stringcc-governance/` with its own MIT license and a JSON/subprocess boundary.

`release/SOURCE_FREEZE_v7.0.json` remains the historical source-freeze record for the RC2 product baseline. The post-freeze StringCC addition is explicitly accounted for by `release/commercial_readiness_v7.0_rc2.json` instead of silently rewriting the historical freeze record.

## Licensing boundary

The repository-level `LICENSE` defines SONICRAFT-owned materials as proprietary unless a narrower file/directory license applies. In particular:

- `integrations/stringcc-governance/` remains MIT licensed under its own `LICENSE`;
- third-party code and dependencies remain governed by their original notices and `licenses/THIRD_PARTY_NOTICES.txt`;
- no StringCC MIT grant is allowed to spill over to SONICRAFT proprietary source, models, assets, binaries, or branding.

This licensing boundary is validated by the source gate.

## Software-side items that must be complete before external validation

The source gate and CI verify the following release preparation:

- version and CMake release contract remain `7.0.0-rc2`;
- pinned Steinberg VST3 SDK 3.8.0 commit is unchanged;
- Windows builder retains detached pinned-SDK checkout and provenance output;
- official Validator evidence contract exists and is SHA-bound;
- Cubase / Studio One evidence harnesses exist and remain fail-closed;
- acoustic evidence remains bound to the exact model-manifest SHA and VST3 SHA;
- frontend layout gate, frontend consumer packaging and installed-runtime fallbacks remain intact;
- Python runtime compatibility remains 3.11–3.13 with pinned release dependencies;
- repository, StringCC and third-party licensing boundaries are explicit;
- StringCC governance tests and Python compile checks pass in CI;
- optional StringCC code is not copied into the commercial consumer prebuilt payload;
- no `RC_APPROVED.txt` or public-release approval is fabricated or committed.

## External release blockers — intentionally not claimable from source CI

A commercial binary remains blocked until all of the following evidence exists for the final candidate:

1. Windows x64 release VST3 rebuild and official Steinberg Validator pass for the exact binary SHA-256.
2. Windows ProductShell binary build and visual verification.
3. Cubase real-host QA, including DPI/scaling matrix and all required workflow checks.
4. Studio One real-host QA, including DPI/scaling matrix and all required workflow checks.
5. Final trained model pack with a real `release_model_manifest.json`, `commercial_safe=true`, `release_approved=true`, and verified model-file hashes.
6. RTX 5090 acoustic QA bound to both the final model-manifest SHA-256 and exact VST3 SHA-256, including a real v6.2 checkpoint verification.
7. `FINAL_GATE_V70.bat` pass.
8. For public release: code-sign the final VST3, regenerate all binary/host/acoustic evidence for the signed SHA, verify Authenticode, then pass `PUBLIC_RELEASE_GATE_V70.bat`.

Signing changes the VST3 hash. Evidence from an unsigned binary must never be reused for the signed public artifact.

## CI policy

`.github/workflows/commercial-source-readiness.yml` runs the source/compliance gate and the StringCC bridge validation on pull requests and on pushes to `main`.

`.github/workflows/windows-vst3-validate.yml` is also enabled for pull requests so a Windows Server CI build can catch source/build/Validator regressions before merge. This CI build is useful preflight evidence, but it does not substitute for the required real Cubase, Studio One, ProductShell visual, GPU/acoustic, or final signing validation.

## Release state

Machine-readable status: `release/commercial_readiness_v7.0_rc2.json`.

Expected state before real-machine validation:

- `source_commercial_ready = true`
- `commercial_binary_approved = false`
- `public_release_approved = false`

The project must remain in that state until the external evidence gates pass.
