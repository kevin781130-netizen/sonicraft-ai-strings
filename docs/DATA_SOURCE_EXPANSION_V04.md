# Data source expansion v0.4

## Admitted or conditionally admitted

- **Ghent AR violin dataset (2023), CC BY 4.0**: use professional First/Second Violin avatar audio + motion as bow/performance prior. Do not let amateur participant audio dominate final timbre.
- **Sanidha, CC BY 4.0**: studio clean violin multitracks. Valuable for bow continuity and real-player texture, but Carnatic pitch ornamentation is style-specific; do not use it to supervise Mandarin-ballad pitch/portamento policy. Access currently requires a Georgia Tech guest/VPN request.
- **MusicNet, per-recording audit**: use only PD/CC0/CC-BY tracks after metadata audit. Chamber/string mixes are for context/realism critic, not isolated timbre.
- **Wikimedia Commons PD/CC0 Musopen quartet seed set**: ensemble-reference only. Runtime downloader re-checks license metadata and fails closed.
- **OpenMIC-2018, CC BY 4.0**: optional weak real-world violin/cello context critic; never a final-timbre source.

## Explicitly blocked

- **VIOLET CSV-TD/checkpoints**: VIOLET code is MIT, but the current README says the CSV-TD dataset license is still being worked on; its audio was rendered from a commercial instrument. We clean-room the architecture ideas only and do not ingest CSV-TD/checkpoints into commercial weights.
- **MUSC audio**: repository provides aligned MIDI and reconstructable YouTube performance links; linked recording rights are not cleared for commercial model training.
- **MOSA**: useful research corpus but the public usage text restricts it to research use; do not include without separate written commercial permission.

## Why this matters

Realism training is split into tone, human performance, musical planning and realism-reference pools. A permissive license alone does not make a source acoustically appropriate, and a high-quality source does not become commercial-safe merely because code or a paper is open.
