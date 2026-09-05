# SONICRAFT v3.5 Performance Memory

v3.5 makes the persistent phrase-comp map browseable from the plug-in instead of hiding it inside project state.

## Browser controls
- Follow Playhead: cursor follows the current DAW musical position.
- Previous / Next: pin the browser and move one phrase, wrapping inside the locator range.
- Next Unresolved: jumps to the next phrase in the locator that has no committed take.
- Recall A/B/C/D: chooses a take to review.
- Audition Recall: switches the v3.2 carousel into Manual mode and auditions that take.
- Commit Recall: commits the recalled take to the browser phrase.
- Favorite / Reject Recall: updates persistent review metadata for the recalled take.
- Clear Phrase: removes the committed phrase entry.

## Live status
The Processor reports read-only VST parameter changes for:
- committed take (Unset/A/B/C/D)
- whether the recalled take is Favorite
- whether the recalled take is Rejected
- locator comp coverage
- browser cursor position in the locator

The browser reads and edits the exact v3.4 PersistentPhraseTakeComp used by playback. It is not a duplicated UI cache.

## Project state
State schema v11 persists Follow Playhead, recalled Take, and pinned cursor in addition to the v3.4 comp map.

## Boundary
The Steinberg VST3 SDK / Cubase / Studio One host runtime is not present in this environment. Processor->controller output-parameter reporting is source-contract validated here, but a host-loaded v3.5 binary remains a release gate.
