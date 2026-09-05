# v0.6

- Added explicit AI Vibrato Control Expert behind CC3.
- CC3 now has four active depth anchors (Light/Natural/Deep/Intense) plus Straight; continuous interpolation remains available.
- Added physical vibrato conditioning: depth cents, rate Hz and micro-jitter; delayed onset remains AI-controlled.
- Added host-tempo conditioning: BPM, seconds/beat, note duration in beats, target transition milliseconds and speed profile.
- VST3 preview reads `ProcessContext::tempo` so tempo changes can alter Legato/Portamento/Bow-change timing.
- Added optional CC20 speed profile for Cubase Expression Maps: Auto/Slow/Normal/Fast.
- CC20 now also controls Vibrato slow/normal/fast **rate tendency** while CC3 remains the independent vibrato-depth axis; rate stays free-running rather than beat-synchronized.
- Added small dedicated Vibrato, Transition and Bow residual experts to the HQ renderer.
- Added deterministic rights-cleared vibrato analysis; no restricted dataset is required to generate release labels.
- Added 1,080 focused v0.6 recording rows: 5 CC3 depth anchors x 3 vibrato-rate profiles, plus Legato/Portamento/Bow-change speed grids across ballad tempos.
- Added research-only Vibrato Analysis Dataset and Violin Technique Dataset candidates to the provenance registry; they remain release-blocked.
- Added 2025 Sorbonne violin acoustics data as a permissive but tiny acoustic-validation candidate.
