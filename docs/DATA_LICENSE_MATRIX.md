# Training-data license matrix — checked 2026-08-30

Commercial release is **fail closed**. Downloadability, research availability, an open paper, or an open-source repository is not enough. Every source entering a release checkpoint must have a documented commercial-use basis and provenance.

| Source | Technical role | Rights basis used here | Release status |
|---|---|---|---|
| University of Iowa MIS | Clean tone / bow texture / dynamics | Official page permits use in any projects without restrictions | **ALLOW** |
| TinySOL | Pitch/dynamic coverage | CC BY 4.0 | **ALLOW** |
| Good-sounds CORA 2025 | Professional violin/cello notes + scales | CORA record: CC BY 4.0 | **ALLOW** |
| Descript DAC | Codec bootstrap | MIT code/weights statement | **ALLOW** |
| MID-FiLD | MIDI dynamics/control prior only | MIT repository/dataset package | **ALLOW** |
| Ghent AR Violin 2023 | Professional violin leader audio + motion prior | CC BY 4.0 | **ALLOW**, avatar/pro leader subset preferred |
| Sanidha | Studio clean violin multitracks / bow continuity | CC BY 4.0 | **ALLOW after access**, acoustic-only style policy |
| Wikimedia PD quartet seed | Ensemble realism/room reference | Per-file PD/CC0 runtime verification | **ALLOW after per-file recheck** |
| MusicNet audited subset | Chamber context / realism critic | Per-recording CC/PD provenance | **ALLOW only for whitelisted tracks** |
| OpenMIC-2018 | Weak real-world violin/cello context critic | CC BY 4.0 dataset; preserve source metadata | **OPTIONAL ALLOW**, critic only |
| VSCO 2 CE | LIVE/articulation reference | CC0 | **LEGALLY ALLOW**, HQ acoustic training disabled |
| Custom Q4 recording | Final legato/vibrato/portamento/phrase anchor | Signed commercial ML + derivative weight rights | **BLOCK until signed, then highest priority** |
| VIOLET CSV-TD/checkpoints | Architecture benchmark only | VIOLET code MIT, but dataset license still pending; audio rendered from commercial VI | **BLOCK** |
| MUSC audio | Research aligned violin performances | Links reconstruct YouTube recordings; audio rights not cleared here | **BLOCK** |
| MOSA | Expressive violin research corpus | Public usage text restricts use to research | **BLOCK unless separately licensed** |
| Philharmonia | Sample reference | Custom terms do not clearly cover learned-weight redistribution | **BLOCK** |
| URMP / QuartSet / EEP | Valuable research corpora | Commercial learned-weight rights not sufficiently clear / NC restrictions | **BLOCK** |
| Wikimedia violin vibrato/technique example | Research vibrato reference | Inspected file carries CC-BY-SA-2.5 / GFDL; learned-weight ShareAlike treatment not cleared | **BLOCK pending legal review** |
| ARME Virtuoso Strings | Q4 timing/performance research | CC-BY-NC-SA / non-commercial research terms | **BLOCK** |
| String Performance Dataset (SPD) | Bow/body/contact research | No explicit commercial ML/model-weight grant verified | **BLOCK** |
| Violin MIDI Performance 2023 | Vibrato/pitch-bend research prior | External-performance provenance / explicit dataset-rights basis not cleared for release | **BLOCK** |
| Single Sound Clarity Strings | Spectral research reference | Explicit standard commercial reuse license not verified | **BLOCK** |

## Training-role separation

1. **Tone/codec:** Iowa + Good-sounds + TinySOL.
2. **Human bow/performance prior:** Good-sounds scales + Ghent professional avatar data + Sanidha after access.
3. **Control/MIDI prior:** MID-FiLD + original generated cue MIDI.
4. **Realism reference:** per-file-cleared Wikimedia PD quartets + audited MusicNet; optional OpenMIC critic only.
5. **Final Mandarin-ballad behavior:** owned Q4 recording session with explicit commercial ML/weight rights.

A dataset can be legally permissive but acoustically unsuitable; it can also be acoustically excellent but legally unusable. Both gates must pass.

## Provenance required in every release checkpoint

- dataset ID + version/DOI
- exact source URL and retrieval date
- local file SHA-256
- license/terms snapshot or signed-rights reference
- preprocessing version
- training role (codec / renderer / control-only / critic / evaluation)

Unknown IDs and release-blocked IDs fail the commercial source gate. v0.7 also requires supervision masks to be target-specific: a trustworthy transition-duration label does not automatically authorize fabricated overlap, attack, softness or bow-timbre targets.
