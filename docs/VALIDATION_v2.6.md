# Validation — v2.6 In-Process Neural Engine

- Native C++ E2E: PASS — 6 voices, 12 neural calls, 9,600 frames, 24 channels.
- Portable SHA-256: PASS against SHA-256("abc").
- Promotion-lock tamper rejection: PASS.
- Six-scenario parity gate mechanics: PASS; authored-pitch mutation is rejected.
- Pure-native bundle audit mechanics: PASS; Python/service artifacts are banned.
- Production promotion mechanics: PASS; post-audit model replacement is rejected.
- Production acoustic parity: NOT CLAIMED — requires real exported production ORT checkpoints and Windows measurements.

## Regression

Re-run in the v2.6 work tree: v1.4, v1.5, v1.6, v1.7, v1.8, v1.9, v2.0, v2.1, v2.2, v2.3, v2.4, v2.5 and v2.6 smoke tests all PASS. v2.1 CPU tiny-pack, Schema-7 acoustic promotion, 24-channel multi-out, native production and ultra-low-latency gates remain intact. Two grouped runs hit aggregate command timeouts; the affected v2.3/v2.5 tests were re-run individually to full PASS.

Exact permissive source locks: 21. Floating HEAD: 0.
