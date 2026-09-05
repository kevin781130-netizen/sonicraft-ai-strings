# v0.6 data scout — Legato / Vibrato / Portamento / Bow-change

Release rule remains fail-closed: a paper/code license is never treated as permission for embedded audio. Commercial model weights accept only sources whose **audio data rights** are compatible with commercial ML training and derivative learned-weight distribution.

## New candidates reviewed on 2026-08-30

- **Violin Technique Dataset (Zenodo 13773807)** — indexed as CC BY and has aligned note/technique CSV + audio, but the actual files are currently restricted. High value for legato/technique timing; blocked until access is granted and the exact record/file terms are snapshotted.
- **Doga Cavdir / MTG vibrato dataset** — technically excellent for no/slow/standard/fast vibrato and pitch trajectories, but embedded recordings have mixed provenance and no single clear commercial learned-weight grant. Research reference only.
- **MIT Bowstroke Database** — technically excellent for measured bowing gesture/audio; the Zenodo CC-BY record is the conference paper, not proof that every underlying database file is commercially trainable. Research reference only.
- **Bach Violin Dataset** — 6.5 h / 17 professional violinists with score alignments, but every recording has its own source license. Candidate for a per-recording audited performance/vibrato subset; blocked as a collection by default.
- **Sorbonne violin acoustics 2025** — Etalab Open License 2.0, permissive; tiny acoustic/physics validation set, not enough for phrase learning.
- **Wikimedia “Violin sounds and techniques”** — CC BY 2.5, contains short vibrato/scale examples; too small and low-fidelity for the renderer, useful as a detector sanity check only.

## What we still need most

The highest-value missing commercial corpus remains dry/close professional western/pop string sessions with exact symbolic controls for:
1. legato transition speed (slow/normal/fast), interval and register,
2. portamento amount + duration,
3. vibrato depth and rate as separate axes,
4. re-bow/bow-change timing and attack character,
5. four-player interaction under the same conductor curve.

The included v0.6 recording cue pack is designed to fill exactly these gaps with owned/licensed recordings instead of diluting the model with unrelated public audio.
