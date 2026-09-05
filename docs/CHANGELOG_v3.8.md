# v3.8 Changelog
- Added local Judge Memory / Personal Taste profile.
- Added confidence-gated five-dimensional preference weights.
- Safety preference cannot become negative; unsafe takes cannot get positive taste bonus.
- Added legacy-compatible 100-byte / opt-in 144-byte Judge results.
- Added local preference update/query/clear protocol and worker-side retry/sync client.
- State schema v13 persists Enable, Strength, Learn and v3.9 gate defaults; profile data stays global/local, outside the DAW project.
- Fixed v3.7 runtime packaging omission for `audio_take_judge_v37.py`.
