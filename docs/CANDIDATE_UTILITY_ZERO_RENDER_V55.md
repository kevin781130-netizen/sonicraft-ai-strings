# v5.5 Candidate Utility Predictor / Zero-Render Pruning

The predictor schedules evidence; it does not replace Audio Judge.

Inputs: Section Character, localized Critic dimensions, post-steer structural scores, Repair Policy, and aggregate history from actual rendered slots.

Confidence modes: low uses v5.4 primary budget; medium can use top-two repairs + D; high can use top-one repair + D. D is mandatory.

Escalation restores all pruned candidates on low Audio margin, predictor/Audio disagreement, Safety failure or Overall failure.

Memory privacy: aggregate numeric context statistics only; no audio/MIDI/score text/filenames. Skipped candidates are never updated.
