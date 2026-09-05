# SONICRAFT AI Strings Q4 v3.2 — Live Retake Carousel

- Added deterministic A/B/C/D Take Bank for host-locator Retake audition.
- Added Manual and Auto Loop modes.
- Added Freeze Current Take.
- Take A preserves the exact base Retake Seed; B/C/D use deterministic seed derivation.
- Added cycle-wrap tracker with jitter/seek rejection threshold.
- Added state schema v8 with backward defaults for v3.1 and older projects.
- Added VST parameters 123–125 without consuming MIDI CC120–127.
- Added `SonicraftRetakeCarouselSmokeV32` and Python source-contract regression.
- Fixed a pre-existing duplicate `scopeBoundaryIndex` declaration in v3.1 `processor.cpp` that could break the actual VST3 source build.
- No acoustic model or training-data changes.
