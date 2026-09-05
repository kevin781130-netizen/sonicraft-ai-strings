# SONICRAFT v2.5 — Ultra-Low-Latency Engine

v2.5 changes no acoustically promoted neural weights. It reduces interactive latency around the existing renderer.

## Windows audio

The preferred Product Shell path is Windows 10+ shared-mode WASAPI through `IAudioClient3`. The shell queries `GetSharedModeEnginePeriod`, chooses a legal minimum engine period, initializes an event-driven shared stream with `InitializeSharedAudioStream`, and runs the audio fill thread under MMCSS `Pro Audio`. If the endpoint is not 48 kHz stereo or IAudioClient3 cannot be opened, the old waveOut path remains available as a compatibility fallback.

This choice is deliberate: modern Windows shared low-period streams can reach the device engine's supported minimum period without automatically taking exclusive ownership of the endpoint.

## MIDI timing

WinMM `MIM_DATA` supplies the driver receive timestamp in callback `dwParam2`, starting at zero on `midiInStart`. v2.5 maps that timestamp to the SONICRAFT sample timeline. v2.4 instead placed MIDI near the middle of a future neural block.

## Adaptive neural quantum

Fresh Note On: 40 ms. Stable realtime: 80 ms. Recovery under deadline pressure: up to 160 ms. The policy is scheduling only; it does not rewrite notes or CC.

## Sustain and boundary safety

CC64 now follows MIDI pedal semantics. Key release while sustain is down is deferred; the effective Note Off is emitted when the pedal is released. A 48-frame dezipper connects successive stereo blocks without adding a full-block lookahead delay.

## Service-free ORT boundary

v2.5 adds a Python/Torch-free ORT bundle audit and a native `OrtGetApiBase` loader probe. This is a candidate boundary, not acoustic promotion. The service-free renderer cannot become default until C++ control construction + renderer + decoder achieve numerical/audio parity and pass existing runtime ABX and artifact-binding gates.

## Formal promotion

`benchmark_ultra_low_latency_v25.py` is fail-closed. Formal evidence requires Windows, a non-MOCK production backend, measured WASAPI stream latency, no cache hits, and passing attack/sustain service deadlines. Engineering smoke on other platforms cannot produce production promotion evidence.
