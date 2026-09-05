# v2.3 Clean-Room Room Capture

The room workflow is independent of Instrument X or any other closed product.

1. `generate_room_sweep_v23.py` creates a SONICRAFT-owned logarithmic sweep.
2. Play that sweep in a room that you are allowed to measure and record the eleven scoring positions as `spot_l`, `spot_c`, `spot_r`, `tree_l`, `tree_c`, `tree_r`, `wide_l`, `wide_r`, `room_l`, `room_r`, and `rear`.
3. `recover_room_irs_v23.py` performs regularized FFT deconvolution, recovers the eleven IR WAVs, and builds the directional room profile used by the runtime.
4. Recovery is fail-closed unless `--rights-confirmed` and a session note are supplied. Recording and recovered-IR hashes are stored in a capture evidence file.

No competitor IR, room measurement, preset or binary is accepted by this workflow.
