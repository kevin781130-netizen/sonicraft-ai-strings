# SONICRAFT AI Strings Q4 v7.0 RC2 — Commercial Release Gate

## What v7.0 changes

v7.0 is not another performance-engine feature release. The v6.2 performance/checkpoint/provenance core and the v6.4 editor/mixer frontend remain frozen.

This RC closes the *release-process* gap:

1. **Pinned VST3 toolchain** — the Steinberg VST3 SDK is pinned to SDK 3.8.0 commit `9fad9770f2ae8542ab1a548a68c1ad1ac690abe0`. A moving `master` checkout is no longer accepted for the commercial RC.
2. **Same-SDK Validator** — the official Steinberg validator is built from that same pinned checkout and its executable hash, exit code, log, SDK commit and plug-in SHA-256 are recorded.
3. **Binary build provenance** — Windows/MSVC build machine, OS, generator, SDK commit and exact VST3 binary SHA-256 are persisted under `release/rc_evidence/`.
4. **Real-host evidence harness** — Cubase and Studio One QA are explicit, interactive, and hash-bound to the VST3 binary tested.
5. **Acoustic evidence harness** — RTX 5090, approved model-manifest file hashes, the exact model-manifest SHA-256, the exact VST3 SHA-256 and a real v6.2 checkpoint verification are required before acoustic approval.
6. **Fail-closed final gate** — missing, skipped or stale evidence blocks RC approval. Public release adds an Authenticode requirement.

## One-click order on the Windows development machine

1. `RC_MACHINE_PREFLIGHT_V70.bat`
2. `RC_BUILD_V70.bat`
3. `QA_CUBASE_V70.bat`
4. `QA_STUDIO_ONE_V70.bat`
5. After the final model pack exists: `QA_RTX5090_ACOUSTIC_V70.bat ...`
6. `FINAL_GATE_V70.bat`
7. For a public signed VST3: sign the VST3 **before the final evidence run**, then regenerate Validator/Cubase/Studio One/acoustic evidence for that signed SHA, run `VERIFY_AUTHENTICODE_V70.bat`, and finally run `PUBLIC_RELEASE_GATE_V70.bat`.

Use `OPEN_RC_EVIDENCE.bat` to inspect the evidence directory.

> **Signing changes the VST3 file hash.** Evidence created for an unsigned binary is intentionally invalid after signing. Do not reuse unsigned Validator/DAW/acoustic reports for the signed public VST3.

## Host QA contract

Both Cubase and Studio One must record a concrete host executable, host version and host-executable SHA-256, then PASS all of the following for the exact same VST3 SHA-256:

- scan/load without blacklist or crash;
- Score / Perform / Retakes / Mix UI;
- MusicXML/MIDI import and four-section note editing;
- project save/reopen with v14 editor/mixer state;
- articulation/expression automation;
- A/B/C/D retake workflow;
- Master/scoring-stage mixer/output stability;
- renderer stopped/fallback behavior without DAW crash;
- offline/bounce rendering;
- 44.1 kHz and 48 kHz sessions;
- at least four simultaneous instances;
- remove/rescan/unload/host-exit stability.

A SKIP is intentionally treated as **BLOCKED**, not PASS.

## Acoustic gate

The acoustic gate is intentionally impossible to pass with placeholder or unapproved weights. It requires:

- Windows;
- NVIDIA GPU detected;
- RTX 5090 detected;
- `release_model_manifest.json` present;
- `commercial_safe=true` and `release_approved=true`;
- every model file SHA-256 matches the manifest;
- acoustic evidence is bound to the exact current `release_model_manifest.json` SHA-256;
- acoustic evidence is bound to the exact current VST3 SHA-256;
- an actual v6.2 checkpoint verify against the test score.

This gate does **not** claim bit-identical audio replay.


## Consumer frontend / BAT packaging

The v6.4 editor is part of the commercial payload, not source-only:

- `App/Frontend/index.html`
- `App/Frontend/editor_server.py`
- `App/Tools/OPEN_INSTRUMENT_EDITOR.bat`
- Manager → **Open Instrument Editor**

The current v6.2 Compile / Auto-Loop / Checkpoint BAT entry points detect both the development source tree and the installed `App/Tools + App/Runtime` layout. When the packaged runtime venv exists, the BATs prefer it instead of depending on a global Python PATH.

## Final approval semantics

`FINAL_GATE_V70.bat` only creates `release/rc_evidence/RC_APPROVED.txt` if all evidence passes and the tested host/validator evidence belongs to the current VST3 SHA-256.

`PUBLIC_RELEASE_GATE_V70.bat` applies the same gate and additionally requires a valid Authenticode signature on the VST3 binary.

No approval marker is committed into this source package.
