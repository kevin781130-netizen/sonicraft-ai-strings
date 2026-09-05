# SONICRAFT v2.1 — Instrument X Clean-Room Benchmark / Gap Closure

## Purpose

Instrument X is treated as a closed-source product benchmark, not a source dependency. SONICRAFT may learn from behavior that Dreamtonics publicly documents or that a normal user can observe through the public product UI. This pass does **not** use Instrument X code, model weights, binaries, presets, proprietary rendered training data, decompilation/disassembly results, or private room measurements.

Public benchmark references reviewed for this pass:
- Dreamtonics Instrument X product page: https://dreamtonics.com/instrument-x/
- Dreamtonics Instrument X First Look (2026-08-26): https://dreamtonics.com/ix-first-look/
- Instrument X manual: https://ix.docs.dreamtonics.com/
- Public system requirements / trials: https://dreamtonics.com/instrument-x/download-free-trials

## Public behavior benchmark

The public product materials describe a neural acoustic-modeling instrument platform with Smart Articulation, a predictive Dynamics lane, targeted AI Performance Retakes, independent overlapping polyphony, MusicXML input, real-world microphone configurations, local/offline inference with no dedicated GPU requirement, AU/VST3/AAX plus standalone operation, and instrument expansions recorded through multiple microphones. The public site reports 8–11 microphones per recording session and 160 MB storage per expansion.

These statements define **test categories**, not implementation instructions.

## v2.1 Clean-Room implementation

| Benchmark pressure | SONICRAFT v2.1 response | Shipping neural cost | Status |
|---|---|---:|---|
| Predictive Dynamics | `runtime/instrument_x_cleanroom.py` derives phrase/register/leap/style intent while preserving the user's lane as anchor | 0 | Implemented, opt-in |
| Smart Articulation | Context resolves only the existing trained 12-class vocabulary; special authored techniques are not casually overwritten | 0 | Implemented, opt-in |
| Performance Retakes | Deterministic Timbre / Dynamics / Vibrato / All retakes using a seed/nonce | 0 | Implemented |
| Strict score authority | Retake does not rewrite note pitch or explicit pitch-bend; Manual remains authored | 0 | Stronger SONICRAFT constraint |
| Overlapping polyphony | Deterministic allocator creates up to 16 independent voice lanes per string part | 0 | Implemented |
| Style instructions | Neutral / Adagio / Allegro / con Fuoco / Pop / Ballade performance-policy layer | 0 | Implemented |
| Spatial scoring stage | Eleven internally addressable virtual feeds using independent micro-delay / air-loss / early-reflection paths | 0 | Architecture implemented |
| MusicXML | Dependency-free MusicXML → SONICRAFT event converter; tempo/dynamics/common string notation preserved conservatively | 0 | Implemented utility |
| No-GPU operation | `SONICRAFT_DEVICE=auto|cuda|cpu`; installer chooses CUDA Torch only when an NVIDIA GPU is present, otherwise CPU Torch | 0 | Functional fallback validated |
| Small consumer model | Existing promoted renderer + VAE64 decoder stays unchanged | 0 | 3,887,433 params / ~7.41 MiB raw FP16 |

## Authority policy

Instrument-X parity is not allowed to weaken SONICRAFT's score authority.

Default behavior:
- Smart Dynamics: **OFF**
- Smart Articulation: **OFF**
- Retake: **OFF**
- Independent Polyphony: **ON**
- Stage: Scoring perspective

AI intervention therefore requires an explicit Director/Retake choice. Authored pitch, note timing/gate, explicit pitch-bend and user CC remain higher-authority inputs than generated helper curves.

## Remaining honest gaps

v2.1 does not claim complete feature parity in the following areas:

1. **Full microphone mixer / DAW routing.** The renderer computes eleven virtual feeds, but the current VST exposes four perspective macros and a stereo result. A first-class 11-fader panel plus independent DAW output busses remains future product work.
2. **Measured directional room decoupling.** SONICRAFT currently uses its own deterministic virtual-stage acoustics. It does not reproduce Dreamtonics' publicly described room-measurement implementation and has no access to their measurements. A SONICRAFT-owned measurement/calibration pipeline would be required.
3. **Native footprint.** Instrument X publicly lists about 160 MB per expansion and no dedicated GPU. SONICRAFT's raw neural weights are far smaller, but the current PyTorch runtime can make the installed footprint much larger. The reduced ORT/native-runtime track remains necessary before claiming deployment-footprint parity.
4. **Platform breadth.** Current commercial focus is Windows VST3. AU, AAX, macOS, and a standalone editor require separate platform builds/QA.
5. **Editor depth.** The MusicXML converter exists, but SONICRAFT does not yet provide a full notation/piano-roll editor equivalent to a dedicated standalone score editor.
6. **Acoustic victory.** Runtime/product parity does not prove that generated strings are harder to distinguish from real players. That still requires the v2.0 rights-cleared Acoustic Promotion training and blind ABX gates.

## Clean-room release audit

Run:

```text
python training/scripts/audit_instrument_x_cleanroom_v21.py --root .
```

The audit blocks competitor binary/model/preset artifact classes from the source package. It is an additional hygiene gate, not a substitute for legal review.
