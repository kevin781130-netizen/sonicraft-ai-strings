# Validation v2.7

Validated in the development environment:
- Python/C++ portable RNG float bit patterns: exact match.
- Short-window Retake smoothing: input/output frame count identical.
- Retake noise: backend-fingerprint invariant.
- Polyphonic quartet context: monophonic lane sees other string parts.
- First-divergence debugger: injected renderer mismatch is located at the correct stage/index.
- v2.6 in-process smoke: PASS.
- v2.0 acoustic promotion: PASS.
- v2.1 clean-room/CPU smoke: PASS.
- v2.2 platform smoke: PASS.
- v2.4 realtime shell: PASS.
- v2.5 ultra-low-latency: PASS.

Production-trained ORT numerical/audio parity remains a release-time gate and is not claimed by synthetic smoke tests.
