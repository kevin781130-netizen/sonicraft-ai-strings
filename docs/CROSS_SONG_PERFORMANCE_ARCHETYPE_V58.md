# SONICRAFT v5.8 Cross-Song Performance Archetype Memory

## Purpose

A new song should not always begin with zero knowledge, but sharing history across unrelated songs can create dangerous bias.

v5.8 introduces a weak cross-song prior based only on the D Original aggregate performance-control envelope.

## Classification

The classifier compares normalized control features against five fixed prototypes:
- Intimate
- Ballad
- Dramatic
- Chamber
- Cinematic

The output includes:
- primary label
- confidence
- secondary label/confidence
- normalized aggregate features
- prototype distances

Labels are UX shorthand for control profiles, not genre recognition.

Low classification confidence (<0.42) blocks Archetype Memory use.

## Memory isolation

Three learning layers remain separate:

1. **Candidate Utility Memory** — actual rendered evidence for an exact local Context.
2. **Similarity Transfer Memory** — reliability of a target<-donor context analogy.
3. **Performance Archetype Memory** — cross-song aggregate evidence conditioned by archetype + local context.

A failure in one layer does not erase evidence in the others.

## Archetype evidence

Only actually rendered slots are learned.

Skipped candidates are untouched.

Evidence is discounted twice:
- at archetype-memory collection time;
- again in candidate score blending.

Archetype evidence is weaker than exact local or v5.7 similarity evidence.

## Hard safety limits

- D Original is mandatory.
- Low-confidence classification: no Archetype transfer.
- Archetype-only evidence: maximum Top-2 + D.
- Top-1 + D: requires target-local evidence.
- Actual Audio Judge remains authority.
- Counterfactual Audit can force full candidate evidence.
- False Prune penalizes only the archetype->context edge.

## Privacy boundary

Persistent Archetype Memory stores aggregate numeric performance/outcome statistics only.

It stores no audio, MIDI, score text, note sequence, song title, filename, identity, or intent hash.
