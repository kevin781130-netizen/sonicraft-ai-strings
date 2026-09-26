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

## VST3 acoustic preview in the DAW

The VST3 custom editor's **Score** page has **Playback Layout**, **Acoustic
Voice** and **Players · Single** menus. Choose **Single**, then one of the
15 instrument names to route incoming DAW MIDI to the selected acoustic preview
renderer. Set **Players** to 1–16 to render independent performers per MIDI note,
with small timing, tuning and stereo placement differences. The performer count
is saved in the DAW project and can be automated. One plug-in instance remains
one instrument; add instances on separate DAW tracks for different instruments.
**Q4 Legacy** keeps the previous voice. **Q4 Multi** continues to use
the four string parts and ignores the acoustic preview selection; its separate
**Legacy Solo Part** menu chooses among those four parts for Single legacy mode.

The browser/standalone score editor is a separate local editor. Its project JSON
and MIDI export do not carry a VST3 plug-in preset or set the DAW's plug-in
parameters; select the acoustic voice in the VST3 editor after loading the MIDI
into the DAW. The 15 voices are procedural acoustic previews, not trained
instrument models or recordings from the benchmark product.

## DAW MIDI performance

Compose notes in the DAW. For an acoustic preview, set Playback Layout to
**Single** and choose the Acoustic Voice in the VST3 editor. Use MIDI channel 1
for ordinary notes and CC1 dynamics, CC3 vibrato, CC11 expression, CC7 volume,
CC64 sustain pedal, CC68 legato, and pitch bend. The 12 articulation keyswitches
are MIDI notes 24–35 (C0–B0 at the plug-in's MIDI numbering). On MIDI channels
5–16, CC21–39 provide optional lane-level performance controls where mapped;
keyswitches on these explicit lanes select their own articulation.

Sustain pedal now starts **off** on newly created instances: note-off releases
the note. An existing saved project restores its saved pedal value. The four
legacy solo parts retain their own Q4 mode and can be selected independently of
the 15 acoustic preview instruments.

All 15 preview choices have independent source spectra and two profile-specific
body modes, and share the same 12 articulation keyswitches, polyphonic MIDI,
CC/pitch automation, pedal release and sample-rate behavior. This makes the
DAW performance interface consistent across instruments. Articulations on wind
instruments are synthetic interpretations; these are not recorded or trained
instrument models.

For acoustic previews, opt-in **Smart Dynamics** now shapes each new note using
velocity and the preceding melodic interval while keeping the authored CC as
the anchor. **Retake Target**, **Amount**, and **Seed** shape the next notes by
deterministic changes to color, dynamics, vibrato, onset feel, or attack. A
locked score does not permit the Micro-Pitch retake to alter authored bend.
These are SONICRAFT procedural retakes, not neural audio retakes, and the Q4
take-judge/comp memory is separate. Existing 16 auxiliary output buses now
carry independent synthetic stage perspectives for the preview. The stage
mixer can rebuild the master from these feeds when the host activates its
outputs. The feeds are derived from the same dry synthesis, not from recorded
or measured microphones; the host must enable the buses to route them.
