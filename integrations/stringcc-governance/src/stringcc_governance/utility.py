from __future__ import annotations
from math import sqrt
from typing import Any
from .models import CandidateProposal
from .evidence import EvidenceLedger


class CandidateUtilityPredictor:
    """Evidence-driven candidate ranking with explicit exploration and change cost.

    It intentionally stays small and dependency-free. Historical accepted/rejected
    trials supply empirical family priors; uncertainty keeps untried families alive.
    """
    def __init__(self, ledger: EvidenceLedger | None = None, *, exploration: float = 0.10, change_penalty: float = 0.025):
        self.ledger = ledger
        self.exploration = max(0.0, float(exploration))
        self.change_penalty = max(0.0, float(change_penalty))

    def score(self, candidate: CandidateProposal) -> dict[str, float]:
        rows = self.ledger.query(family=candidate.family) if self.ledger else []
        phrase_rows = [r for r in rows if str(r.get("phrase_key")) == str(candidate.phrase_key)]
        data = phrase_rows if phrase_rows else rows
        n = len(data)
        if n:
            gains = [float(r.get("local_gain", 0.0) or 0.0) for r in data]
            expected = sum(gains) / n
            variance = sum((g - expected) ** 2 for g in gains) / max(1, n - 1) if n > 1 else 0.04
            uncertainty = sqrt(max(0.0, variance) / max(1, n)) + 0.08 / sqrt(n + 1)
            accept_rate = sum(int(bool(r.get("accepted", False))) for r in data) / n
            expected += 0.015 * (accept_rate - 0.5)
        else:
            expected, uncertainty = 0.0, 0.18
        complexity = len(set(candidate.changed_dimensions)) / 8.0
        acquisition = expected + self.exploration * uncertainty - self.change_penalty * complexity
        return {
            "expected_gain": expected,
            "uncertainty": uncertainty,
            "complexity": complexity,
            "acquisition": acquisition,
            "observations": float(n),
        }

    def rank(self, candidates: list[CandidateProposal]) -> list[tuple[CandidateProposal, dict[str, float]]]:
        ranked = [(c, self.score(c)) for c in candidates]
        ranked.sort(key=lambda x: (x[1]["acquisition"], x[1]["expected_gain"]), reverse=True)
        return ranked
