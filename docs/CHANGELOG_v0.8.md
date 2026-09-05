# v0.8 — Real Recording Mining + Data-Calibrated CC3

## Goal
Move real recordings from a passive timbre/reference pool into a **rights-cleared physical-performance supervision pipeline** without fabricating labels.

## Added
- `training/scripts/audit_real_recordings.py`
  - fail-closed registry check
  - per-file license/source evidence for mixed-license sources
  - SHA-256 provenance
- `training/scripts/analyze_real_performance.py`
  - real-audio F0, RMS, spectral centroid and spectral flux
  - conservative vibrato depth/rate/onset/jitter extraction
  - stable straight-note detection
  - conservative bow-change marker proposals
  - only emits Expert-ready rows when intended-pitch controls exist (aligned NPZ or trusted single-note metadata)
- `fit_vibrato_calibration.py` + `vibrato_calibration.py`
  - CC3 anchors are fitted from real, release-cleared performances
  - Straight + Light + Natural + Deep + Intense remains the user model
  - 0–127 remains continuous; the four active layers are anchors, not sample switches
- `apply_vibrato_calibration.py`
  - maps measured cents to calibrated CC3 values before Expert/HQ training
- Vibrato training now has **per-output masks**:
  - depth_known
  - rate_known
  - onset_known
  - jitter_known
  A straight/no-vibrato note can supervise depth=0 without inventing a meaningless vibrato rate.
- `PREP_REAL_RECORDINGS_V08.bat`
- `CONTINUE_TRAIN_V08.bat`

## Source scouting changes
New blocked/watch entries:
- Violin Technique Dataset 2024: technically valuable but files restricted.
- Violin spherical microphone dataset: 2.9GB / 23 expressions, but no explicit license was visible in the verified record.
- High-resolution Violin MIDI Dataset: excellent pitch-bend trajectories, but release rights were not verified and linked YouTube audio is never harvested.
- skx300 vibrato dataset: repo Apache-2.0 does not automatically clear embedded audio provenance.
- OrchideaSOL: metadata CC BY does not mean audio is CC BY; audio is governed by IRCAM Forum terms.

Optional Public-Domain-only historical source was added for realism statistics; BY-SA items stay excluded by default.

## Philosophy
**Real audio is useful only when both the acoustic evidence and the rights evidence are trustworthy.**
Unknown labels stay masked. Unknown licenses stay blocked.
