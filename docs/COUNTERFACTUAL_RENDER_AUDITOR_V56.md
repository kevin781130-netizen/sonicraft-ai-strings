# SONICRAFT v5.6 Counterfactual Render Auditor

## Purpose

v5.5 can make a high-confidence pruning decision that appears internally consistent: predicted winner matches the actually rendered winner and Audio margin is healthy. The remaining blind spot is a candidate that was never rendered and would have won anyway.

v5.6 measures that blind spot directly.

## Counterfactual audit

For a scheduled audit window:
1. Preserve the hypothetical v5.5 initial budget and winner.
2. Render all candidate slots needed for full A/B/C/D evidence.
3. Recompute Audio Judge ranking.
4. Compare the full-evidence winner with the hypothetical winner.

False Prune requires:
- full winner was originally pruned;
- Overall gain >= 0.025;
- full winner Safety >= 0.35;
- full winner Overall >= 0.35.

## Deterministic schedule

Audit frequency is based on prune-opportunity count per context:
- 12 when stable;
- 6 when recent FPR >= 10%;
- 4 when recent FPR >= 20%;
- 1 while the context is disabled.

This avoids nondeterministic QA behavior.

## Confidence multiplier

After at least two audits, recent False-Prune Rate reduces predictor confidence. This can widen a Top1+D budget to Top2+D or the v5.4 Section Character budget before a hard disable is reached.

## Disable / recovery

Disable is local to a Utility context, never global.

Disable when:
- recent audits >= 4 and FPR >= 25%; or
- at least two False Prunes occur in the latest four audits.

While disabled, predictor pruning is suspended for that context. Counterfactual calibration continues on every prune opportunity.

Recovery requires four consecutive clean audits. The clean recovery streak becomes the new recent calibration window so stale failures cannot immediately re-disable the context.

## Learning boundary

Audit rendering is real rendering. Therefore an audited slot is legal input to v5.5 Utility Memory.

A slot that remains genuinely skipped is still never learned.

Counterfactual Audit Memory itself stores only aggregate audit outcomes and never stores audio/MIDI/score text.
