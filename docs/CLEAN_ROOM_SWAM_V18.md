# v1.8 Clean-Room Bowed-String Policy

Audio Modeling SWAM String Sections is used only as a public behavioral reference for identifying important user-observable bowed-string phenomena and control coverage. SONICRAFT does not inspect or copy proprietary implementation details.

Allowed inputs include public manuals/marketing/release notes, ordinary bowed-string acoustics literature, permissively licensed scientific source, and independently authored SONICRAFT equations/tests.

Prohibited inputs include SWAM binaries, reverse engineering/decompilation/disassembly, AMData, presets extraction, proprietary weights/source, SWAM-rendered training corpora, private assets, or copying proprietary UI/implementation. Clean-room modeled audio is tagged `training_origin=modeled`, `final_timbre_anchor=false`, and is confined to the 20% physics lane.

The behavioral test matrix includes continuous bow-energy/expression response, bow pressure, contact-point movement, bow direction/lift, attacks, legato/portamento/runs, low-pressure airy behavior, high-pressure scratch tendency, vibrato development and section-player dispersion. Passing these tests means SONICRAFT implements the behavior independently; it does not claim equivalence to SWAM's sound or internal algorithm.
