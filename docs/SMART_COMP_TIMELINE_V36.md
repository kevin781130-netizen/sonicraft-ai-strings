# SONICRAFT v3.6 Smart Comp Timeline

v3.6 adds an eight-phrase timeline viewport over the persistent Performance Memory.

Each visible phrase shows:
- Committed: Unset / A / B / C / D
- Smart Pick: rule-based candidate priority / A / B / C / D

The viewport follows the existing Memory cursor and slides over the host locator range.

## Smart Rank
Smart Rank is deliberately not marketed as audio-quality prediction. Without listening to rendered audio or training a preference model, the plug-in cannot know which take sounds "best."

The ranking is deterministic and uses:
- the actual v3.2 A/B/C/D derived Retake nonce, quantized to the same 8-bit nonce used by the renderer;
- the active Retake target;
- Retake amount;
- MIDI Authority Lock for Micro-Pitch eligibility;
- the same target-dimension salt family used by the v2.8 Retake contract;
- human Favorite/Reject review metadata.

Favorite dominates the heuristic. Reject removes a candidate. With no review metadata, Conservative / Balanced / Adventurous modes prioritize lower / medium / higher deterministic variation profiles.

## Actions
- Smart Audition: loads the current phrase's suggestion into Manual Take audition.
- Smart Commit: commits the current suggestion.
- FAV ONLY: commits unresolved phrases that have exactly one human Favorite.
- AUTO UNRESOLVED: commits heuristic Smart Picks for unresolved phrases in the Locator. This is intentionally labeled heuristic and remains undoable as one fixed-memory batch edit.

## State
State schema v12 persists Smart Rank Mode. Timeline output itself is derived from the v3.4/v3.5 persistent comp state and needs no duplicate storage.

## Boundary
VST3 source/output-parameter wiring is implemented, but Steinberg VST3 SDK and target DAW toolchains are unavailable in this environment. Host-loaded timeline rendering remains a release gate.
