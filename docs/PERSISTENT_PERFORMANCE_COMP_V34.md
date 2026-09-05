# SONICRAFT v3.4 Persistent Performance Comp

v3.4 persists phrase-level A/B/C/D comp decisions in the DAW project state.

## Stored per phrase
- phrase key
- committed Take A/B/C/D
- four-bit Favorite mask
- four-bit Reject mask

## Editing
- Commit Current Phrase
- Commit Take Across Locator
- Favorite Current Take
- Reject Current Take
- Clear Comp
- internal fixed-depth Undo / Redo (16 snapshots)

Favorite and Reject are mutually exclusive for the same take. The realtime comp table remains fixed at 128 entries and all edit history uses fixed-size storage; no heap allocation is introduced in the audio callback.

## State safety
Processor state schema is v10. The Controller explicitly accepts v10 and consumes the exact comp-record payload before reading the four part-control blocks. Invalid counts, take indexes or metadata masks fail closed.

## Boundary
The state layout has source-contract and standalone-core validation here, but no Steinberg SDK is installed, so actual Cubase/Studio One binary save-close-reopen validation remains a target-host release gate.
