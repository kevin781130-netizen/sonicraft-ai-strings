# v1.2 RC2

- Commercial model integrity manifest with SHA-256 and fail-closed runtime loading.
- Release source gate rejects enabled blocked/unknown datasets.
- Held-out release metric gate for MIDI lock, CC3 vibrato monotonicity, tempo transitions, renderer dropout/fallback and ABX.
- Static MSVC runtime configuration for consumer VST3.
- Official VST3 validator is mandatory for the commercial pipeline.
- Pinned CUDA runtime baseline: PyTorch 2.8.0 / torchvision 0.23.0 / torchaudio 2.8.0 cu128; descript-audio-codec 1.0.0; soundfile 0.14.0.
- Authenticode script now signs/validates VST3 binary, renderer launcher, Manager and Setup.
- Third-party notices for VST3/VSTGUI and Descript DAC.
- Consumer release builder stages only approved, hash-verified models.
- Windows CI workflow template for VST3 build/validator.
- Sample-offset-accurate VST3 automation merge for CC1/CC3/CC11/CC20 and all part parameters; automation is applied before same-sample note-on.
- Fixed runtime vibrato validity: generated inference no longer falsely teacher-forces zero measured vibrato physics; CC3 now drives the learned Vibrato Expert cleanly.
- MANUAL/ASSIST/AUTO is now transmitted to the renderer as a cache-keyed performance profile; hidden bow intervention is restrained in Manual and progressively enabled in Assist/Auto.
- Removed the inactive Auto Divisi control from the public RC UI until true section-divisi rendering exists.
- Phrase cache keys now include the approved model fingerprint, preventing stale audio after model updates.
