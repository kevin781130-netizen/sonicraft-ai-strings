# Source verification snapshot — 2026-08-30

This is an engineering provenance snapshot, not legal advice. Refresh it before shipping a commercial checkpoint.

## Enabled commercial sources

### University of Iowa MIS
Official: https://theremin.music.uiowa.edu/MIS.html

The official site states that the recordings may be downloaded and used for any projects without restrictions. Modern string recordings include high-resolution anechoic material. Use as the principal public tone/codec anchor, not as proof of real phrase/legato coverage.

### TinySOL
Official: https://zenodo.org/records/3685331
License: CC BY 4.0. Use only violin/viola/violoncello ordinary notes for pitch/dynamic coverage.

### Good-sounds CORA 2025
DOI: https://doi.org/10.34810/DATA2314
License: CC BY 4.0 on the 2025 CORA distribution. Professional studio violin/cello notes and scales. Keep this distinct from older distributions with different terms.

### Ghent AR violin dataset
DOI: https://doi.org/10.5281/zenodo.8147435
License: CC BY 4.0. The repository includes stereo WAV audio and motion/joint-angle data. Prefer the professional First/Second Violin avatar/section-leader subset for performance priors; amateur participant recordings are not final timbre anchors.

### Sanidha
Official: https://ccml.gtcmt.gatech.edu/data/Sanidha/
License: CC BY 4.0. About eight hours of studio-quality Carnatic multitracks; violin is provided as clean multitracks. Current download flow requires a Georgia Tech guest/VPN request. Use only as acoustic/bow-continuity supervision unless pitch-ornament style is explicitly masked, so Carnatic gamaka does not become the Mandarin-ballad portamento policy.

### MusicNet
Official: https://zenodo.org/records/5120004
The archive contains freely licensed/public-domain classical recordings and per-recording provenance. Commercial use in this project is **per-track audited only**; do not bulk-assume one blanket license. Chamber/string mixes are realism/context references, not isolated timbre training.

### Wikimedia Commons public-domain quartet references
Per-file pages are the authority. v0.4 ships a small seed list of Musopen String Quartet FLAC pages that show public-domain dedication/CC0/public-domain metadata. The downloader re-queries Commons extmetadata at runtime and refuses files that do not still resolve as PD/CC0.

### OpenMIC-2018
Official: https://zenodo.org/records/1432913
License: CC BY 4.0. It contains 10-second naturally occurring music excerpts with violin/cello labels. Because these are mixed recordings, they are optional weak realism/context critic data only.

## Blocked even though technically attractive

### VIOLET CSV-TD/checkpoints
Code: https://github.com/User-tian/VIOLET
VIOLET code is MIT, but the current README states that the CSV-TD dataset license is still being worked on/coming soon. CSV-TD audio was rendered with the commercial Joshua Bell Violin instrument. v0.4 may clean-room the architecture/control ideas, but does not ingest CSV-TD audio/checkpoints into commercial release weights.

### MUSC
Repository: https://github.com/MTG/violin-transcription
The repository publishes aligned MIDI and reconstructable YouTube performance links rather than a clean commercial-use grant for the underlying audio recordings. Block from commercial synthesis training.

### MOSA
Repository: https://github.com/yufenhuang/MOSA-Music-mOtion-and-Semantic-Annotation-dataset
The project includes rich professional violin audio/semantics, but public usage text restricts the dataset to research. Block unless separate written commercial permission is obtained.

### URMP / QuartSet / EEP / Philharmonia
Keep blocked until explicit commercial ML-training and learned-weight distribution rights are documented for this use.

## Decision rule

The model must get closer to real recording by improving **source precision**, not by quietly widening the rights boundary. Unknown or ambiguous data never enter a commercial release checkpoint.
