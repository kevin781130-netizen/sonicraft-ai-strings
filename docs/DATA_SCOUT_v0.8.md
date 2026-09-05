# Data Scout v0.8 — Real recordings first, rights first

Verified 2026-08-30.

## Useful now
- **Good-sounds CORA 2025** — CC BY 4.0; professional studio violin/cello single notes and scales. Primary public source for real CC3 depth statistics when notes are suitable.
- **Iowa MIS** — unrestricted official source statement; excellent 24/96 isolated string timbre/dynamics anchor.
- **TinySOL** — CC BY 4.0; controlled note coverage.
- **Ghent AR violin dataset** — CC BY 4.0; professional avatar leader audio/motion useful for acoustic/bow priors.
- **MusicNet** — Zenodo describes 330 freely licensed recordings and OpenAIRE indexes the record as CC BY. v0.8 still retains track provenance/hashes and uses it chiefly for chamber-context/realism work rather than direct isolated-control supervision.

## Watch / blocked
- **Violin Technique Dataset (2024)** — audio + note/technique CSV, but files are restricted. Do not bypass access.
- **Dataset of Violin Recordings with Spherical Microphone Arrays** — 2.9GB, 32 microphones, 23 expressions; verified record did not expose an explicit license. Block until clarified.
- **High-Resolution Violin MIDI Dataset** — 34h-equivalent aligned MIDI/pitch-bend trajectories from 22 violinists are technically ideal for vibrato timing study, but the commercial-compatible dataset license was not verified. Never harvest its linked YouTube audio.
- **skx300 vibrato_dataset** — ground truth is valuable for analyzer research, but repo license is not treated as an audio-rights grant for all embedded sources.
- **OrchideaSOL** — audio is controlled by IRCAM Forum terms; metadata CC BY is not the audio license.

## Search rule
A source does not enter release training merely because:
- a paper is CC BY;
- GitHub code is MIT/Apache;
- a Zenodo record is downloadable;
- the composition is public domain.

The **recording/performance data rights** must independently support commercial model training/derived weights, or be sufficiently permissive (CC0/CC BY/PD with provenance) for the intended use.
