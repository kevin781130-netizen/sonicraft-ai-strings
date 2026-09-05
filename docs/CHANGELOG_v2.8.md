# SONICRAFT AI Strings Q4 v2.8 — Performance Commander

## Goal
Close the non-training-data product/control gap against Instrument X without inflating the acoustic model.

## Implemented
- Smart Divisi is now a real note-routing path for single-source Q4 MIDI. Authored multi-channel Q4 remains authoritative.
- Retake expands to 7 dimensions: Timbre, Dynamics, Vibrato, Micro-Pitch, Timing Feel, Bow/Attack, All.
- MIDI Authority Lock prevents Retake from altering authored pitch-bend/micro-pitch unless explicitly unlocked.
- Phrase Director adds phrase arch, leap and cadence-aware residual performance shaping.
- Ensemble Looseness creates deterministic per-player bow/vibrato separation without changing written notes.
- Runtime policy bit contract is shared across VST shadow renderer, Python/ORT service and native C++ client.
- Scoring stage expands from 11 to 16 virtual feeds: Master + 16 stereo aux = 34 channels / 17 stereo buses.
- 24-channel v2.7 responses remain accepted by the VST/client path for compatibility.
- Added a dependency-free C++ Performance Commander smoke and Python runtime smoke.

## Deliberate non-claims
The five new stage feeds are virtual geometry outputs, not claims of five additional recorded microphone positions. Acoustic quality still depends on promoted production weights.
