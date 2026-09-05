# Changelog — v2.1 Instrument-X Clean-Room Parity

- Added public-behavior-only Clean-Room performance intelligence module.
- Added opt-in Smart Dynamics and Smart Articulation with authority-safe defaults.
- Added six performance styles: Neutral, Adagio, Allegro, con Fuoco, Pop, Ballade.
- Added deterministic targeted Retakes for timbre, dynamics, vibrato, or all hidden performance dimensions.
- Retake intentionally never rewrites authored note pitch or explicit pitch-bend.
- Added deterministic up-to-16-voice independent polyphony per string part.
- Added phase-coherent eleven-feed virtual scoring-stage engine and four VST-facing perspective macros.
- Added dependency-free MusicXML → SONICRAFT event converter and Windows batch entry point.
- Added functional `SONICRAFT_DEVICE=auto|cuda|cpu` backend selection and CPU-only installer path when no NVIDIA GPU is detected.
- Removed unnecessary torchvision/torchaudio from the preferred runtime installation path.
- Added v2.1 C++ VST parameters/state for Director, Retake, Stage and Polyphony; state version 5 remains backward-readable from v3/v4 projects.
- Added clean-room source-package audit.
- Preserved Schema-7 v2.0 acoustic model-pack compatibility; no v2.1 neural parameter increase.
