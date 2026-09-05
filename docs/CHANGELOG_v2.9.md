# SONICRAFT AI Strings Q4 v2.9 — DAW-Native Performance Compiler

## Why this exists
Instrument X includes a proprietary internal note editor. SONICRAFT v2.9 deliberately takes the opposite host-first route: keep Cubase/Studio One as the editor and compile ordinary MIDI into transparent, editable orchestral performance MIDI.

## New
- Dependency-free Standard MIDI File parser/writer (Python stdlib only).
- One-click `COMPILE_MIDI_TO_Q4.bat` drag/drop workflow on Windows.
- Smart chord/register divisi to Vln I / Vln II / Viola / Cello.
- Phrase segmentation with conservative phrase-arch dynamics.
- Existing 12-class articulation suggestions encoded as normal C0–B0 keyswitch MIDI.
- CC1 dynamics and CC3 vibrato suggestions are emitted as normal editable controller data.
- Type-1 output contains a conductor/tempo track plus four explicit Q4 tracks/channels.
- `.performance.json` sidecar records every note decision and a deterministic Retake Matrix plan.
- MIDI Authority Lock is structural: pitch, onset and duration are copied from source notes; the compiler only chooses part and performance metadata.

## Non-claim
This compiler improves orchestration/workflow. It does not improve acoustic model quality and does not invent untrained articulation classes.
