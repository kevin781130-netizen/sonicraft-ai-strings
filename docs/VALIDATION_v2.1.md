# Validation — v2.1 Instrument-X Clean-Room Parity

## Passed

- Python compileall: training / runtime / installer tools.
- v1.4 through v1.9 regression smoke paths passed in this working tree.
- v2.0 Acoustic Promotion smoke passed (stereo/phase codec tournament, robust ABX, Promotion Seal, Schema 7).
- v2.1 Clean-Room smoke passed:
  - Manual predictive dynamics identity;
  - opt-in predictive dynamics modification;
  - smart articulation short/fast mapping;
  - deterministic same-seed Retake and different-seed variation;
  - 3 simultaneous notes → 3 independent lanes;
  - 11 virtual spatial feeds;
  - MusicXML chord/dynamics/articulation conversion;
  - CPU tiny-pack model load and 3,840-frame stereo render.
- Shadow Renderer localhost mock IPC: 48,000 frames / 384,000 bytes.
- Runtime-only isolation import passed with training/source tree absent.
- VSTGUI XML parsed successfully.
- C++ edited files passed static delimiter/declaration consistency checks; a Windows/MSVC VST3 binary build is still required for binary validation.
- All new runtime modules are included by installer/prebuilt staging lists.
- 21 permissive source locks use exact 40-character commits; floating HEAD = 0.
- Clean-Room package audit passes with no prohibited competitor artifacts detected.

## Not claimed

- CPU fallback is functionally validated, not benchmarked as real-time on every supported laptop.
- Eleven internal virtual feeds are not yet exposed as eleven independent VST faders/output busses.
- No claim of Dreamtonics' measured-room algorithm parity.
- No AU/AAX/macOS/standalone binary has been built in this package.
- No claim of acoustic superiority until rights-cleared training + blind ABX passes the existing Acoustic Promotion contract.
