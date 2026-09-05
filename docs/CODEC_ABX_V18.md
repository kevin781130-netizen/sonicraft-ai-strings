# v1.8 Strings Codec ABX Ladder

All codec challengers must be evaluated on the same rights-cleared string material and the same REAL80/MODEL20 policy. Upstream generic checkpoints are benchmark/reference artifacts only unless separately audited; product weights must be SONICRAFT-trained/approved.

Primary candidates:

- SONICRAFT Strings VAE64: 48 kHz, 64-d, 1600x downsampling, 30 Hz latent; current compact decoder candidate.
- ACE-Step 1.5 1D VAE geometry: 48 kHz stereo, 64-d, 1920x downsampling, 25 Hz latent; challenger for lower temporal state density.
- Descript DAC: trainable MIT codec baseline.
- SoundReactor/Oobleck and KVAE-Audio: continuous-latent architecture/quality references.

A codec is promoted only if it clears blind string reconstruction tests, transient/legato/portamento/vibrato preservation, section texture, latent generation quality under a fixed renderer budget, decoder size, latency/VRAM and commercial provenance. Lower latent rate alone is not sufficient.
