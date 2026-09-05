# SONICRAFT v5.9 Multi-Archetype Mixture / Soft Classification

## Why

Hard classification creates avoidable edge cases when a D Original performance lies between two or three control prototypes.

v5.9 replaces hard borrowing with a soft mixture.

## Weighting

Prototype distances are converted by a bounded softmax.

Only the closest three components are considered.
Components below 0.08 are removed and the remainder re-normalized.

Mixture confidence measures fit to the overall prototype manifold. It does not punish healthy ambiguity between two nearby prototypes.

## Evidence

Each component contributes aggregate v5.8 rendered evidence scaled by:
- component weight
- mixture confidence
- v5.8 component trust
- v5.9 component->context trust.

## Learning

Only rendered slots learn.

A rendered observation is distributed to each active component proportional to its mixture weight.

No skipped slot receives evidence.

## Audit

False-Prune penalties are weight-aware.

A dominant component receives more penalty than a weak component for the same failed decision.

The calibration is stored in v5.9 only and does not mutate:
- v5.8 archetype trust
- v5.7 target<-donor edges
- v5.5 exact Utility.

## Safety

Mixture-only evidence can at most unlock Top-2 + D.

Top-1 + D requires actual target-context evidence.

D Original remains mandatory.
