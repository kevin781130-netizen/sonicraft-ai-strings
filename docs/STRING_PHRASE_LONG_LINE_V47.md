# v4.7 Phrase-Level Bow Energy & Vibrato Continuity

v4.7 converts a v4.6 linked chain into a long-line phrase.

The score graph records phrase ID, contour, apex, bow reserve, dynamic momentum, vibrato-rate target and flags.

The phrase planner reshapes existing gesture anchors conservatively:
- Dynamics Energy follows the phrase arc.
- Bow Pressure and Contact Point follow long-line intensity.
- Vibrato Depth evolves toward phrase intensity instead of restarting per note.
- Bow reserve is consumed by duration/pressure and reset at explicit/solver bow changes.

Runtime activation uses CC38=1/127 followed by the normal Gesture Amount. No new control family is added.

HQ control output populates vibrato depth in cents and vibrato rate in Hz only inside marked v4.7 phrase windows. Old files remain zero/legacy in those fields.

This is deterministic performance planning, not new acoustic training.
