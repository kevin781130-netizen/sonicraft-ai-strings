# SONICRAFT v4.4 Ensemble Bow & Phrase Coordination

## Goal
Turn four independently-planned string parts into a coordinated quartet/section performance plan while preserving written score authority.

## Phrase segmentation
Each explicit String Voice lane is segmented into phrases using rests, connection/slur state and note gaps. Phrase IDs are stored in the Score Graph.

Phrase endings may receive a small breath shortening, scaled by tempo and articulation. Ties and connected slurs block automatic breathing.

## Ensemble attack clusters
Notes beginning within a 1/32-quarter tolerance are grouped when at least two string sections participate.

Each group receives:
- part roles (`lead`, `inner`, `foundation`);
- a target bow direction where notation allows;
- deterministic attack offsets by part and desk;
- optional coordinated bow-change anchor.

Attack spread is deliberately small and bounded to ±8 ms.

## Bow synchronization
Explicit `up-bow` / `down-bow` marks have highest authority.

If only one direction is explicitly requested, unforced bowed notes may align with it. If both directions are forced simultaneously, the solver preserves both and reports `explicit_bow_direction_conflict`.

## Phrase Breath
Phrase breath is encoded as 0..20 ms shortening at note release. Short/pizzicato material receives a smaller value; expressive phrase endings can receive a slightly larger breath.

## Runtime Bus
- CC36 -> opcode 120 -> signed attack offset
- CC37 -> opcode 121 -> phrase breath

The HQ renderer performs actual event-time adjustment. The layer is opt-in and no recognized opcode means no timing rewrite.

Preview uses a lightweight attack/tightness/transition approximation because sub-block host scheduling is not validated without a real VST3 host.

## Acoustic honesty
This is an ensemble execution layer. It does not add new samples, per-string timbral training, real desk recordings, or conductor-model training.
