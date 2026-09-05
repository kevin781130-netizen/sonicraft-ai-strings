# v4.5 Continuous String Gesture Graph

The v4.5 planner creates seven note-internal anchors for bowed notes. It uses existing physical/ensemble context and never adds a new acoustic articulation class.

## Curves
- Bow Speed: planning dimension used to derive kinetic response.
- Bow Pressure: authored into CC31.
- Contact Point: authored into CC33.
- Dynamics Energy: authored into CC22.
- Vibrato Evolution: authored into CC23.
- Portamento: authored into CC34.
- Micro Pitch: authored into CC39, lane-local, +/-50-cent contract; planner itself normally stays within much smaller bounds.

## Gesture Amount
CC38 opens/closes a gesture interpolation window. HQ runtime interpolates the control snapshots and physical curves only within that explicit window. No window = legacy behavior.

## Acoustic honesty
Bow speed and kinetic response are control/planning dimensions mapped into already-supported model controls. This release does not claim that the neural model was newly trained on measured bow-speed trajectories or per-string continuous timbre.
