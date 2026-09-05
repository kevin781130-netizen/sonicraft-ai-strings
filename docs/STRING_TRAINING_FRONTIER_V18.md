# SONICRAFT AI Strings Q4 v1.8 — String Training Frontier

## Release invariant: real sound authority, modeled physics authority

The acoustic training lane is fixed to **0.80 probability mass from rights-cleared real strings and 0.20 from SONICRAFT clean-room modeled bowed strings**. This is probability mass, not a file-count target. Curriculum reweights quality and rare instrument/articulation cells *inside* each lane without moving the 80/20 boundary.

Real recordings are the only final timbre authority. Codec adversarial “real” targets are sampled from the real lane only. Modeled reconstruction is down-weighted and modeled rows carry exact bowed-string physics labels for scarce controls/transitions. The clean-room lane must never contain SWAM audio, binaries, presets, AMData, weights, decompiled material or captured proprietary training assets.

## Training stack retained after source scouting

High-value permissive training/reference lanes include VIOLET; DDSP-Violin 2026; SSSSM-DDSP; NESS; Descript DAC; SoundReactor VAE; Oobleck; EnCodec; KVAE-Audio; stable-audio-tools; BigVGAN; Shortcut Models; MeanFlow; TorchCREPE; TorchFCPE; and ACE-Step 1.5's VAE as a codec challenger. AudioCraft code may be studied where its code license permits, but non-commercial upstream model weights are excluded.

The consumer VST does not ship these repositories. Third-party source snapshots are development/training/reference material, exact-commit pinned, with large/pretrained assets excluded.

## Clean-room physics labels

The independent SONICRAFT bowed teacher can emit exact supervision for bow speed, bow force, contact point, vibrato depth/rate, friction residual, spectral slope, contact-notch depth, residual energy, section pitch spread, section timing spread and section bow spread. Section-mode synthesis creates controlled multi-player dispersion without granting modeled waveforms final timbre authority.

## Promotion rule

Architecture and smoke tests do not establish acoustic superiority. A candidate enters the product model pack only after rights-cleared training and blind listening/ABX plus MIDI-authority, transition, vibrato, latency, VRAM and package-size gates.
