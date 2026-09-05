# SONICRAFT AI Strings Q4 v6.4 — Instrument Editor / Stage Mixer Frontend Convergence

## Goal

v6.4 closes the two product-surface gaps that remained after the v6.2 reproducibility/provenance freeze:

1. a coherent instrument editor workflow comparable in shape to a modern AI performance instrument;
2. a first-class scoring-stage microphone mixer using the 16 stereo feeds already exposed by the renderer/processor architecture.

This release deliberately does **not** add another performance brain, memory system, judge, compiler, or renderer.

## Product workflow

The frontend is organized into four primary workspaces:

- **Score** — four string sections, piano-roll note editing, articulation bar, note/phrase inspector, predictive-dynamics lane, import/export.
- **Perform** — performance style, phrase director, smart articulation/dynamics, divisi/polyphony and section controls.
- **Retakes** — controlled A/B/C/D retake intent, score comparison, favorite/reject and phrase commit workflow.
- **Mix** — Master + 16 stereo scoring-stage feeds: Spot L/C/R, Tree L/C/R, Wide L/R, Room L/R, Rear, Mid L/R, Far L/R, Gallery.

## Two frontend surfaces, one core

### VST3 source UI

`resource/SONICRAFT_AI_Strings_Q4.uidesc` is reorganized into Score / Perform / Retakes / Mix pages using the existing VSTGUI stack. It adds automation-facing stage-mixer ParamIDs 810–828 and keeps the existing section templates.

### Dependency-free local Instrument Editor

`frontend/index.html` + `frontend/editor_server.py` implement a portable local editor without Electron, Node packages, JUCE, Qt, React or a database service.

The editor provides:

- Select / Draw / Erase piano-roll editing;
- drag-to-move and right-edge resize;
- four independent string sections;
- undo / redo;
- MusicXML import;
- Standard MIDI File import and export;
- editable articulation/expression inspector;
- editable predictive-dynamics lane;
- project JSON save/reopen;
- retake A/B/C/D intent, score cards, favorite/reject/commit;
- Master + 16-feed mixer;
- Windows bridge to the existing v6.2 Compile and Auto-Loop BATs.

The browser editor does not fork SONICRAFT performance logic. Its Project → MusicXML bridge feeds the existing v6.2 `score_expression_graph` and compiler pipeline.

## Open-source convergence decision

The research pass intentionally preferred architecture/interaction patterns over dependency accumulation.

- **VSTGUI** — retained as the native plug-in UI framework. Its BSD-style license is compatible with the existing commercial distribution direction.
- **sfizz-ui** — used as evidence that a production audio plug-in UI can successfully stay on a VSTGUI/BSD route. No sfizz source was copied.
- **AudioKit PianoRoll** — MIT; interaction ideas such as pitch-row shading and touch/editor affordances informed the clean-room editor design. No source was copied.
- **MIT piano-roll projects** — used only as interaction references for selection, dragging, zooming and velocity/expression-lane behavior.
- **JUCE / GPL DAW and synth projects** — intentionally not vendored. Migrating the project or copying GPL code would add licensing/build/product risk without improving the frozen core.

`licenses/FRONTEND_OPEN_SOURCE_NOTICES_V64.txt` records the research boundary.

## Audio compatibility rule

Stage Mixer is **disabled by default**. Existing model/legacy master output remains the default path, preserving the v6.2 behavior until the user explicitly activates the v6.4 mixer. This is a compatibility decision, not a claim of bit-identical audio across runtimes.

## Project state

The plug-in source state version is advanced from **13 → 14** only to persist:

- Stage Mixer enable;
- Master gain;
- Output gain;
- 16 feed gains.

The UI page itself is not part of the acoustic checkpoint identity.

## Release boundary

v6.4 is a **source/frontend final candidate**. This package does not claim:

- rebuilt Windows v6.4 VST3 binary;
- Steinberg Validator pass;
- Cubase real-host pass;
- Studio One real-host pass;
- final trained SONICRAFT acoustic model quality;
- bit-identical audio replay.

Those remain binary/acoustic validation gates, not frontend feature work.
