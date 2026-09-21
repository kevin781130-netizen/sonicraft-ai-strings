# SONICRAFT AI Strings Q4 v7.0.0-rc2 — Release Notes

## Release purpose

v7.0 RC2 is the commercial-release convergence candidate. It does not introduce a new performance brain; it freezes the v6.2 performance/checkpoint/provenance core and the v6.4-era editor/mixer product surface while closing release engineering, reproducibility, packaging, compliance, and evidence gates.

## Product surface

The candidate includes:

- strings performance compilation and A/B/C/D repair/retake workflow;
- reproducible project checkpoints and acoustic-runtime provenance;
- Score / Perform / Retakes / Mix editor workflow;
- MusicXML and MIDI import/editing;
- expression and performance-control editing;
- Stage Mixer with master plus scoring-stage feeds;
- packaged Manager, ProductShell, local editor, runtime tools, and VST3 build path;
- fail-closed release gates bound to exact binary/model hashes.

## Release engineering

v7.0 RC2 pins the Steinberg VST3 SDK to version 3.8.0 commit `9fad9770f2ae8542ab1a548a68c1ad1ac690abe0` and records build/Validator provenance for the exact VST3 artifact. Host and acoustic evidence contracts are also hash-bound so stale evidence cannot approve a changed binary or model pack.

The commercial installer carries the SONICRAFT proprietary license notice plus third-party notices. The optional `integrations/stringcc-governance/` bridge remains separately MIT licensed and is intentionally excluded from the consumer VST3/prebuilt payload.

## Optional StringCC governance bridge

StringCC governance bridge v1.1 is present as an optional developer interoperability component using a clean-room JSON/subprocess boundary. It provides conductor intent, bounded candidate steering, evidence-driven utility ranking, counterfactual audit, append-only evidence, and governed repair orchestration without importing SONICRAFT proprietary source into the bridge.

It is not required to run the commercial consumer plugin and is not part of the signed consumer payload.

## Validation status

Software-side commercial-readiness checks are automated by:

- `.github/workflows/commercial-source-readiness.yml`
- `scripts/rc_source_gate_v70.py`
- `FRONTEND_LAYOUT_GATE_V70.bat`
- `.github/workflows/windows-vst3-validate.yml`

Passing source CI means the source/compliance/package contracts are internally consistent. It does **not** by itself approve the commercial binary.

## Required evidence before commercial distribution

The release remains blocked until the final candidate has all required Windows build/Validator evidence, ProductShell real-machine verification, Cubase and Studio One real-host QA, an approved final model pack, RTX 5090 acoustic QA bound to the exact model and VST3 hashes, and a passing `FINAL_GATE_V70`.

Public distribution additionally requires Authenticode signing, regeneration of all hash-bound evidence for the signed binary, and a passing `PUBLIC_RELEASE_GATE_V70`.

## Known truth boundaries

This release does not claim bit-identical audio replay across changing GPU/runtime/model environments. It also does not treat skipped host checks, placeholder model weights, stale evidence, unsigned-vs-signed hash mismatches, or source-only test success as commercial approval.
