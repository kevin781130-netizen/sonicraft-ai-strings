# SONICRAFT v2.2 — Platform Kill Gap

## Scope

v2.2 does not change the promoted acoustic renderer/decoder. It closes product-platform gaps around the same sound core.

### 1. Master + 11 true DAW feeds

The VST declares twelve stereo output buses: one Master and eleven auxiliaries: Spot L/C/R, Tree L/C/R, Wide L/R, Room L/R, Rear. Auxiliary buses are not active by default. When the host exposes only Master, the renderer keeps the legacy two-channel response. When aux buses are active, request flag bit 25 asks the service for 24 interleaved float channels. The host mixer therefore becomes the primary eleven-feed fader/multi-out surface without duplicating another large mixer UI inside the plug-in.

### 2. Clean-room room calibration

`training/scripts/build_room_profile_v22.py` converts eleven user/SONICRAFT-owned or explicitly licensed IR WAVs into a directional profile. No competitor room measurements, IRs, binaries or presets are included. The profile supplies per-feed delay, gain, pan and short L/R FIR response to the same stage renderer.

### 3. No-PyTorch deployment challenger

`runtime/ort_model_backend.py` imports no PyTorch. NumPy builds controls, executes few-step integration around ONNX Runtime renderer sessions, decodes the latent, resamples, and produces either stereo or 34-channel stage output. This is a deployment challenger, not an acoustic promotion by itself.

### Promotion rule

ORT/native deployment may become the default only when the actual trained promoted models pass all of the following: staged runtime <=160 MiB; no Torch/TorchVision/TorchAudio/PyTorch/DAC framework files; per-file SHA-256 binding; numerical audio parity; runtime transparency ABX with at least five valid listeners and sixty trials; and an already valid Schema-7 Acoustic Promotion. Failure keeps Torch as the default.

## What v2.2 does not claim

The source package does not contain production-trained ONNX/ORT weights, so it does not claim a measured <=160 MiB final installer, real Torch-vs-ORT acoustic parity, or runtime ABX success. Full Windows VST3/Cubase activation of all twelve buses must still be tested on the target Windows/DAW build. The Linux validation can compile the shadow client and exercise the 34-channel IPC contract, but it is not a Cubase certification.
