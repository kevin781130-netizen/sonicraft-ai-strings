# SONICRAFT v3.7 Validation

Validated 2026-09-01 in the available Linux environment.

## v3.7 Audio-Aware Take Judge — PASS
- NumPy DSP synthetic test:
  - authored dynamics-following take outranks flat dynamics;
  - clipping/spike take loses Safety and Transition;
  - broadband chatter loses Transition;
  - human Favorite dominates DSP tie;
  - Reject excludes a candidate.
- TYPE_JUDGE renderer protocol:
  - 8-byte Judge config;
  - 100-byte fixed Judge result;
  - A/B/C/D valid mask;
  - Favorite B wins four identical mock renders.
- Two repeated Judge requests reuse exactly four A/B/C/D waveform cache entries.
- v3.2 Take nonce C++ contract at base seed 0.37: 94 / 187 / 209 / 143 after renderer 8-bit quantization.
- Shadow Judge transport translation unit compiles standalone with C++20 / pthread / sockets.
- Judge DSP runs in renderer service / worker path, not the realtime Processor audio callback.

## Correctness guards — PASS
- Phrase identity guard: stale Judge start sample cannot be Auditioned/Committed into another phrase.
- Configuration identity guard covers resolved scoped Retake/Director state, seed, amount, target, authority, assist/style, Smart Dyn/Art, looseness, stage, polyphony, mode/lookahead, layout/instrument/divisi, part controls, tempo and Favorite/Reject review masks.
- In-flight Judge result captures its own config token; a newly queued request cannot relabel an older result.
- Pinned-phrase policy snapshot is resolved at the phrase center rather than from the current playhead state.
- Beat↔sample tempo timeline supports pinned phrase mapping across observed tempo changes.
- Native tempo map smoke: 120 BPM -> 60 BPM transition maps beats 2/4/6 to samples 48000/96000/192000 at 48 kHz.

## Controller/state fix — PASS
- State schema remains v12; Judge scores are derived/ephemeral.
- Controller accepts v12.
- Transient state reset no longer overwrites restored Follow Playhead, Recall Take or Smart Rank Mode.
- Controller source lexical brace-balance regression passes.

## Regression — PASS
- v3.6 Smart Comp Timeline source + C++ smoke.
- v3.5 Performance Memory source + C++ smoke.
- v3.4 Persistent Comp source + C++ smoke.
- v3.3 Phrase Comp source + C++ smoke.
- v3.2 Retake Carousel source + C++ smoke.
- v3.1 Host Locator Scope source + C++ smoke.
- v3.0 Host Command Lane / Project Bridge.
- v2.9 Performance Compiler.
- v2.8 Performance Commander.
- Torch / NumPy performance-control parity.
- ORT no-Torch backend: 12000 x 34.
- Mock standard render PASS.
- Mock multi-out: 12000 x 34.
- Native in-process engine: 9600 frames / 34 channels.
- Portable RNG regression.
- Promotion Guard + tamper rejection.
- Clean VST-independent CMake build.
- UIDESC XML parse.
- ParamID range/collision check.

## Release boundary
The Steinberg VST3 SDK and target Windows/macOS DAW toolchains are not installed in this environment. Therefore:
- a rebuilt v3.7 VST3 binary is NOT claimed;
- Steinberg Validator is NOT claimed;
- actual Cubase/Studio One Audio Judge UI, Processor output-parameter display, save/reopen and host automation validation remain release gates;
- bundled historical executables must not be labeled v3.7 validated binaries.

No acoustic model weights or training data were changed.
