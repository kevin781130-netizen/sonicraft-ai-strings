# SONICRAFT AI Strings Q4 v3.0 — Host Intelligence Bridge

- Added DAW-native Performance Command Lane on reserved MIDI CC 102–119.
- Mapped command CCs to AI Assist, style, Smart Dynamics/Articulation, 7-D Retake, Authority Lock, Phrase Director, Ensemble Looseness, Auto Divisi, stage, polyphony, AI Mix, Look Ahead, Layout Mode, Single Instrument and Humanize.
- Added region-scoped Project Bridge that modifies command CCs only and restores pre-region state at the end boundary.
- Added deterministic `.bridge.json` history with SHA-256 provenance and effective values.
- v3.0 compiler now embeds a tick-0 host-intelligence snapshot and schema-2 note IDs.
- Added one-click Retake, Director and Clear bridge BAT entry points.
- Fixed Torch/CUDA performance-control drift versus NumPy/ORT: Phrase Director, Ensemble Looseness and newer Retake dimensions now share one behavior contract.
- Added Python/C++ command-contract smoke, Project Bridge non-destructive smoke, Torch↔NumPy control parity smoke and a VST mapping source-contract smoke.
- Acoustic architecture/weights/data are intentionally unchanged.
