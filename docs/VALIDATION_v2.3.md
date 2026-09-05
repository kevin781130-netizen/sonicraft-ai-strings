# Validation — v2.3 Native Production Pass

Validated in the source/package environment:

- standalone-only CMake configure/build without VST3 SDK;
- standalone -> mock renderer -> stereo WAV end-to-end;
- standalone -> mock renderer -> 24-channel WAV end-to-end;
- synthetic known-IR room sweep -> recording -> deconvolution -> eleven-feed profile;
- room capture rights-confirmed evidence and hashes;
- v2.3 embedded-ORT footprint policy mechanics;
- runtime benchmark evidence mechanics;
- native promotion pass on valid synthetic evidence;
- post-audit model replacement rejection;
- v2.2 and prior regression suites remain the compatibility baseline.

Not claimed until Windows production artifacts exist: actual <=160 MiB Windows bundle, real Torch↔ORT trained-model parity, real runtime ABX, production-hardware p95 RTF, realtime standalone audio/MIDI GUI, macOS AU/AAX signing/notarization.
