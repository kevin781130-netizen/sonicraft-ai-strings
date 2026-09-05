# SONICRAFT Instrument Editor v6.4

This is the dependency-free local product frontend for the v6.2 performance/runtime core.

## Normal launch
Run `SONICRAFT_EDITOR_V64.bat`.

## Debug launch
Run `DEBUG_EDITOR_V64.bat`. Console output is retained in `logs/frontend_v64/editor_debug.log`.

## What is real in this frontend
- Four-section piano-roll editor with Select / Draw / Erase, move and resize.
- Undo / redo.
- MusicXML and Standard MIDI import.
- Project JSON save/load.
- MIDI export.
- Note articulation and expression inspector.
- Editable predictive-dynamics lane.
- Retake A/B/C/D intent, scoring UI, favorite/reject/commit memory workflow.
- 16-feed scoring-stage mixer plus Master/Output.
- Local bridge to the existing `COMPILE_MUSICXML_STRINGS_v62.bat` and `AUTO_LOOP_STRINGS_v62.bat` on Windows.

## Architectural boundary
The editor does not implement a second compiler or acoustic renderer. It produces editable source intent and delegates actual compile/render work to the frozen v6.2 runtime. This prevents the UI from becoming another source of performance logic drift.
