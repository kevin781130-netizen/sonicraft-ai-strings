# Validation — v2.4 Realtime Product Shell

Engineering validation covers the protocol and product-shell boundary, not a claim of production Windows audio latency.

Validated in the source/package smoke:

- VST3-independent C++20 rolling-window core compiles;
- repeated 160 ms render windows preserve timeline look-back and return 24-channel multi-out;
- 11-feed + master downmix returns valid stereo audio;
- formal realtime benchmark detects MOCK and refuses promotion;
- AUTO selects ORT only with intact native-promotion/footprint/artifact evidence;
- post-audit ORT artifact tampering falls back to Torch;
- Product Shell promotion binds a PE64 Product Shell + Renderer Service bundle and rejects post-audit tampering;
- Windows source contract uses Win32/WinMM/waveOut and retains Smart Dynamics/Articulation OFF by default;
- v2.0 Acoustic Promotion, v2.1 authority/parity, v2.2 platform and v2.3 native-production regressions remain mandatory before packaging.

Not claimed without a Windows production machine:

- ASIO/WASAPI-exclusive latency;
- sub-10 ms live latency;
- production ORT first-audio latency;
- real MIDI hardware compatibility across all devices;
- signed installer / Windows Defender reputation.

## Final source-tree regression

Final source-tree regression passed for v1.4, v1.5, v1.6, v1.7, v1.8, REAL80/MODEL20, schema-5 policy, v1.9 Sound Forge, v2.0 Acoustic Promotion/schema-7, v2.1 Instrument-X Clean-Room parity + CPU tiny-pack, v2.2 Platform Kill Gap, v2.3 Native Production Pass and v2.4 Realtime Product Shell.

Additional final checks:

- 21 permissive source locks, all exact 40-hex commits; floating HEAD = 0.
- renderer PING reports backend identity; mock returned `READY:MOCK`.
- 24-channel multi-out IPC returned 12,000 frames / 24 channels.
- runtime-only import succeeded with `torch` explicitly blocked.
- v2.4 cross-platform simulation produced six consecutive 160 ms rolling windows and a valid stereo WAV.
