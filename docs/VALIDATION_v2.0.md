# v2.0 Validation Record

Status: **engineering-validated acoustic-promotion machinery; production acoustic victory remains blind-validation dependent**.

## Regression

The working tree passed the existing v1.4, v1.5, v1.6, v1.7, v1.8 and v1.9 smoke suites plus v2.0 smoke.

## v2.0-specific gates

- Sound Forge v2.0 curriculum and fixed REAL80/MODEL20 policy: PASS.
- Rights/duplicate/audio fail-closed behavior: PASS.
- Acoustic phrase segmentation with real + modeled coverage: PASS.
- Stereo/phase/harmonic codec tournament: PASS on synthetic smoke fixtures.
- Codec quality-first selection and compactness tie-break: PASS.
- Powered schema-2 codec ABX scorer: PASS on chance-level smoke fixture.
- Powered generated-vs-real ABX scorer: PASS on chance-level smoke fixture.
- Unsupported tournament winner blocks release when no audited runtime adapter exists: PASS.
- Candidate checkpoints cannot satisfy final promotion binding until sealed: PASS.
- Promotion seal preserves model tensor digest: PASS.
- Schema-7 release manifest/integrity/commercial gate: PASS.
- Acoustic-promotion evidence tampering rejection: PASS.
- Standard and Full-HQ v2.0 Model Pack creation: PASS.
- Schema-5/6 backward verification path: retained.

## Runtime

Mock Shadow Renderer IPC returned 48,000 stereo frames / 384,000 bytes. Runtime-only isolation imports succeed without `training/` or `src/` present.

## Size

No new v2.0 consumer neural parameters were added. Current raw FP16 core remains approximately 7.41 MiB (renderer + VAE64 decoder only).

## What this does not prove

Synthetic smoke fixtures do not prove that SONICRAFT is indistinguishable from a real string section. Actual rights-cleared Violin I / Violin II / Viola / Cello training and blinded human listening must populate the real release evidence before an acoustic-promotion claim is valid.
