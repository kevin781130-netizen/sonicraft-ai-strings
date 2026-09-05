# SONICRAFT AI Strings Q4 v1.9 — Engineering Validation

Validated in this source package on 2026-08-31:

- Python `compileall` for `training/` + `runtime/` — PASS.
- v1.4 regression smoke — PASS.
- v1.5 regression smoke — PASS.
- v1.6 regression smoke — PASS.
- v1.7 regression smoke — PASS.
- v1.8 Frontier Context smoke — PASS.
- v1.8 REAL80/MODEL20 + clean-room/physics smoke — PASS.
- v1.8 schema-5 release-policy backward compatibility — PASS after schema-6 introduction.
- v1.9 Sound Forge synthetic intake — PASS: 8 eligible REAL + 4 eligible MODELED, registry rights gate, quality fields, SHA-256 and duplicate rejection exercised.
- v1.9 Forge-weighted curriculum — PASS at exactly 0.800 / 0.200 probability mass.
- blocked-source Forge row — correctly REJECTED.
- v1.9 parameter-free physics/latent geometry loss — finite forward/backward PASS.
- v1.9 codec tournament — PASS; quality-first winner logic exercised.
- codec efficiency tie-break — PASS; lower latent-state candidate wins only when quality is inside the configured tie window.
- codec ABX scoring path — PASS with deterministic chance-level synthetic response fixture.
- schema-6 synthetic release construction + runtime integrity verification — PASS.
- schema-6 commercial release gate — PASS on synthetic test artifacts only.
- v1.9 Standard + Full-HQ model-pack construction — PASS.
- post-approval codec-ABX evidence tamper — correctly REJECTED by SHA-256 integrity gate.
- Shadow Renderer localhost mock IPC — PASS: 48,000 frames / 384,000 bytes; finite non-zero stereo payload.
- runtime-only isolation with training/source tree absent — PASS.
- v1.9 renderer params: 2,606,296.
- VAE64 decoder params: 1,281,137.
- combined raw FP16 theoretical weights: ~7.41 MiB, excluding inference framework/runtime.
- v1.9 Sound Forge / tournament / physics geometry adds **0 neural runtime parameters**.
- permissive source lock: 20 exact commits; floating `HEAD` count 0.
- ACE-Step 1.5 and `acestep.vst3` pinned commits rechecked against current upstream GitHub on 2026-08-31; both pins were still the latest observed commits.

## What this validation does not claim

The package does **not** contain the user's final rights-cleared acoustic training corpus or trained v1.9 production checkpoints. Therefore this engineering validation does not claim:

- acoustic superiority over v1.8;
- that SONICRAFT VAE64 beats ACE-Step/Oobleck or DAC on real held-out string recordings;
- codec perceptual transparency;
- generated strings indistinguishable from real recordings;
- one/two-step Shortcut parity with a fully trained HQ teacher.

Those claims remain fail-closed behind real Sound Forge reports, held-out codec tournament, codec ABX and generated-vs-real blind release metrics.
