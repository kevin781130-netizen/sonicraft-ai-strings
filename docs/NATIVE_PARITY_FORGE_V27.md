# v2.7 Native Parity Forge

v2.7 adds no consumer neural parameters. Its purpose is to make the Python/ORT reference and the C++ in-process engine reproducibly comparable before native promotion.

## Portable contracts
- Initial latent noise: FNV-1a64 key → SplitMix64 → Box-Muller, implemented in Python and C++.
- Retake noise uses the same portable generator and deliberately excludes backend/model fingerprint, so changing runtime does not change the take.
- Polyphonic rendering uses two data sources: the monophonic lane owns written note/CC controls; full ensemble events own quartet/phrase context.
- Short realtime smoothing always returns the original frame count.

## Trace order
`raw_controls → frontier_context → initial_latent → renderer_velocity → latent_after_step → final_latent → decoder_audio → stage_audio → final_mix`.

`compare_native_trace_v27.py` reports the first stage/index/value beyond tolerance instead of only a final WAV score. `minimize_parity_case_v27.py` delta-debugges event cases against an external replay command.

## Promotion
A formal v2.7 parity promotion requires six passing scenarios: Manual, Assist, Polyphony, Q4/Phrase, Retake, and Multi-Out, plus an already valid v2.6 in-process promotion. Production ORT checkpoint/audio parity is still required before native becomes the default consumer path.
