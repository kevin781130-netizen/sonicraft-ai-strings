# SONICRAFT v5.7 Context Generalization / Similarity Transfer

## Purpose

Reduce cold-start render cost for a new phrase context without treating borrowed experience as local truth.

## Context representation

The transfer layer uses the same interpretable context vocabulary as v5.5:

`Section Character | Critic dimensions`

Example:

- donor: `build|transition`
- donor: `build|latent_playability`
- cold target: `build|latent_playability+transition`

The two donors may contribute discounted evidence to the target. A `climax|transition` donor may not.

## Similarity

Same Section Character is mandatory.

For Critic dimension sets:

`Jaccard = intersection / union`

Minimum accepted Jaccard = 0.34. Exact context keys are not treated as transfer; they remain local evidence.

## Donor reliability

A donor must have enough actual-render Utility evidence. Donor v5.6 Audit state can reduce its weight or block it entirely.

Effective transfer weight combines:
- context similarity;
- donor Audit confidence multiplier;
- target<-donor edge trust.

Transferred evidence is capped and additionally discounted when blended into Candidate Utility.

## Aggressive-pruning guard

Transfer alone may accelerate a cold target from v5.4 budget to Top2 repairs + D.

Top1 repair + D requires >=1.5 average units of actual target-context evidence. No donor collection can bypass this gate.

## Transfer-edge calibration

v5.6 Counterfactual Audit remains the truth source.

If a pruned slot becomes the full-evidence winner with >=0.025 Overall gain, v5.7 records the event on every transfer edge used by that prediction.

False-Prune:
- edge trust falls;
- repeated failures may disable that edge.

Clean audits:
- edge trust recovers gradually;
- four clean audits can recover a disabled edge.

The donor Utility record and donor exact-context Audit record remain untouched.

## Privacy / persistence

Similarity Transfer Memory stores aggregate edge calibration only:
- target key;
- donor key;
- trust;
- audits;
- false-prune count;
- clean streak;
- recent boolean outcomes / gains.

It does not store audio, MIDI, score text, filenames, or identity.
