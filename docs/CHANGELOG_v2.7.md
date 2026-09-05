# Changelog v2.7

- Added cross-language bit-stable portable RNG for latent and Retake generation.
- Retake identity no longer depends on runtime/model fingerprint.
- Fixed ORT polyphony context slicing: lane controls + full ensemble context.
- Fixed short-window smoothing length expansion in Retake/Director paths.
- Added stage-addressable parity trace utilities and first-divergence reporter.
- Added delta-debug parity case minimizer.
- Added v2.7 six-scenario parity promotion evidence contract.
- Added focused `SonicraftParityRngSmokeV27` target so parity CI does not rebuild unrelated VST/product targets.
- No consumer neural parameters added.
