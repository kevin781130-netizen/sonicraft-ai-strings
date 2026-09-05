# Commercial-safe data expansion, v0.3

## Newly admitted: Good-sounds CORA 2025
Official dataset: https://doi.org/10.34810/DATA2314

The 2025 CORA distribution is explicitly CC BY 4.0. It contains studio monophonic single-note and scale recordings by 15 professional musicians, including violin and cello. The pipeline should keep only good-sound / scale-good material and store dataset version + hashes + attribution.

Important: the older Zenodo Good-sounds record is CC BY-NC 4.0. v0.3 treats the two distributions as separate provenance IDs. Only the CORA 2025 copy is allowed into a commercial checkpoint.

Training use:
- violin/cello acoustic-quality supplement
- real scale phrasing / note-transition statistics
- quality-filtered note tone
- not a substitute for a rights-owned dedicated Mandarin-ballad transition session

## Newly admitted: MID-FiLD (MIDI only)
Official repository: https://github.com/pozalabs/MID-FiLD
License: MIT.

Contains string_violin / string_viola / string_cello / string_double_bass MIDI classes and fine-level dynamics metadata, plus mood and track-role labels. It is safe for symbolic performance-control pretraining but contributes no acoustic timbre.

## Optional only: FSD50K CC0 bowed-string clips
FSD50K has mixed clip licenses. Any optional ingestion must whitelist **only CC0** clips and bowed-string labels. It is never a final timbre anchor because recording quality/context are inconsistent.

## Still blocked for commercial release
URMP, QuartSet, EEP/QUARTET, MOSA/MUSC and any source without a direct commercial ML-training / derivative-weight path remain blocked. Research usefulness does not override release provenance.
