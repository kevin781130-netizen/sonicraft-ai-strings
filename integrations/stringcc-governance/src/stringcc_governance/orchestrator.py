from __future__ import annotations
from dataclasses import asdict
from typing import Any, Callable
from .models import ConductorIntent, CandidateProposal
from .conductor import ConductorSteerer
from .utility import CandidateUtilityPredictor
from .audit import CounterfactualAuditor
from .evidence import EvidenceLedger

Evaluator = Callable[[CandidateProposal], dict[str, Any]]


class GovernedRepairOrchestrator:
    """Governed candidate loop designed to sit above StringCC's renderer/optimizer.

    evaluator(candidate) must return at least ``local: {loss: ...}``. Optional
    ``whole`` and ``adjacent`` maps make the audit stricter.
    """
    def __init__(self, ledger: EvidenceLedger, *, steerer: ConductorSteerer | None = None,
                 predictor: CandidateUtilityPredictor | None = None, auditor: CounterfactualAuditor | None = None):
        self.ledger = ledger
        self.steerer = steerer or ConductorSteerer()
        self.predictor = predictor or CandidateUtilityPredictor(ledger)
        self.auditor = auditor or CounterfactualAuditor()

    def run_phrase(
        self,
        *, phrase_key: str,
        base_overrides: dict[str, Any],
        intent: ConductorIntent,
        baseline: dict[str, Any],
        evaluator: Evaluator,
        phrase_features: dict[str, Any] | None = None,
        max_candidates: int = 4,
    ) -> dict[str, Any]:
        candidates = self.steerer.propose(phrase_key, base_overrides, intent, phrase_features)
        ranked = self.predictor.rank(candidates)[:max(1, int(max_candidates))]
        accepted: list[dict[str, Any]] = []; trials: list[dict[str, Any]] = []
        for cand, utility in ranked:
            result = evaluator(cand)
            audit = self.auditor.audit(
                baseline.get("local", baseline), result.get("local", result),
                baseline_whole=baseline.get("whole"), candidate_whole=result.get("whole"),
                adjacent_baseline=baseline.get("adjacent"), adjacent_candidate=result.get("adjacent"),
                changed_dimensions=cand.changed_dimensions,
            )
            rec = {
                "phrase_key": phrase_key,
                "candidate_id": cand.candidate_id,
                "family": cand.family,
                "overrides": cand.overrides,
                "changed_dimensions": cand.changed_dimensions,
                "expected_effect": cand.expected_effect,
                "utility": utility,
                "metrics": result,
                "audit": audit.to_dict(),
                "accepted": audit.accepted,
                "local_gain": audit.local_delta,
                "causal_confidence": audit.causal_confidence,
            }
            self.ledger.append(rec); trials.append(rec)
            if audit.accepted:
                accepted.append(rec)
        accepted.sort(key=lambda r: (float(r["causal_confidence"]), float(r["local_gain"])), reverse=True)
        winner = accepted[0] if accepted else None
        return {
            "schema": "stringcc.governance.run.v1",
            "phrase_key": phrase_key,
            "intent": asdict(intent.clamped()),
            "baseline": baseline,
            "trials": trials,
            "winner": winner,
            "selected_overrides": winner["overrides"] if winner else dict(base_overrides),
            "fallback_to_baseline": winner is None,
        }
