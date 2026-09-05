# Changelog — v2.5 Ultra-Low-Latency Engine

- Added adaptive 40/80/160 ms neural scheduling; fresh attacks begin at 40 ms.
- Added `IAudioClient3` shared-mode event-driven WASAPI output with MMCSS audio thread and waveOut fallback.
- Added use of WinMM driver MIDI timestamps (`dwParam2`) instead of block-midpoint placement.
- Fixed sustain semantics: key-up under CC64 is deferred until pedal release.
- Added low-cost block-boundary dezipper / final-release taper.
- Added v2.5 latency benchmark and fail-closed promotion contract.
- Added Python/Torch-free in-process ORT candidate audit and direct ORT DLL loader probe.
- Neural renderer/decoder parameter count unchanged.
