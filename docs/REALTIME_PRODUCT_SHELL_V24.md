# SONICRAFT v2.4 — Realtime Product Shell

v2.4 does not change the acoustically promoted renderer or VAE64 decoder. It closes the user-facing product gap between the localhost neural renderer and a playable standalone instrument.

## Architecture

`MIDI -> Timeline -> rolling neural windows -> Master + 11 feeds -> native mixer -> Windows audio output`

The rolling-window engine keeps prior Note On / CC / articulation events in look-back context, so sustained notes do not need to be retriggered at every preview buffer. Default preview quantum is 160 ms. Final AUTO/HQ rendering still uses the normal acoustic-promotion path.

## Native Windows shell

The Windows product shell intentionally uses platform APIs only: Win32 controls, WinMM MIDI input and waveOut audio output. It does not add JUCE, Qt, SDL or an external GUI framework. The shell exposes MIDI/audio device selection, active part, Assist/Auto policy, six performance styles, Smart Dynamics, Smart Articulation, Retake target/amount/seed, independent polyphony and a Master + 11-feed scoring-stage mixer.

Smart Dynamics and Smart Articulation remain OFF by default. MIDI note pitch, authored pitch bend and authored CC keep Strict MIDI Authority.

## Runtime AUTO policy

AUTO is fail-closed. ORT is selected only when the v2.3 native-runtime promotion and its footprint evidence exist, the evidence IDs match, the promoted artifact bundle still exists, and every bound artifact SHA-256 still matches. Otherwise AUTO selects Torch. Explicit `SONICRAFT_RUNTIME=torch|ort` remains an expert override.

## Realtime promotion

A small runtime is not automatically a playable runtime. v2.4 adds a production benchmark for first-audio latency and deadline misses. Formal Realtime Product Promotion requires:

- an already promoted native runtime;
- a non-MOCK realtime benchmark with at least the requested timing threshold;
- a PE32+ x64 Product Shell and Renderer Service bundle;
- <=170 MiB shell/runtime bundle by default;
- no Torch payload in the promoted lightweight shell bundle;
- per-file SHA-256 binding, rechecked at promotion time.

Mock timing is engineering-only and is explicitly rejected by the benchmark promotion path.
