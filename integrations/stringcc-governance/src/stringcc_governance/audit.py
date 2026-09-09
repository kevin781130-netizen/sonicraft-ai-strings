from __future__ import annotations
from typing import Any, Optional
from .models import AuditResult


def _metric(d: dict[str, Any] | None, key: str) -> Optional[float]:
    if not d or key not in d or d[key] is None:
        return None
    try:
        return float(d[key])
    except (TypeError, ValueError):
        return None


class CounterfactualAuditor:
    """Fail-closed audit for local repairs before causal credit is retained."""
    def __init__(
        self,
        *, min_local_gain: float = 1e-5,
        max_whole_regression: float = 2e-4,
        max_adjacent_regression: float = 0.012,
        max_changed_dimensions: int = 4,
    ):
        self.min_local_gain = float(min_local_gain)
        self.max_whole_regression = max(0.0, float(max_whole_regression))
        self.max_adjacent_regression = max(0.0, float(max_adjacent_regression))
        self.max_changed_dimensions = max(1, int(max_changed_dimensions))

    def audit(
        self,
        baseline_local: dict[str, Any],
        candidate_local: dict[str, Any],
        *,
        baseline_whole: dict[str, Any] | None = None,
        candidate_whole: dict[str, Any] | None = None,
        adjacent_baseline: dict[str, float] | None = None,
        adjacent_candidate: dict[str, float] | None = None,
        changed_dimensions: list[str] | None = None,
    ) -> AuditResult:
        changed = list(dict.fromkeys(changed_dimensions or []))
        b = _metric(baseline_local, "loss"); c = _metric(candidate_local, "loss")
        if b is None or c is None:
            return AuditResult(False, 0.0, 0.0, None, 0.0, ["missing_local_loss"], changed_dimensions=changed)
        local_delta = b - c  # positive = improvement
        reasons: list[str] = []; warnings: list[str] = []
        if local_delta < self.min_local_gain:
            reasons.append("insufficient_local_improvement")

        whole_delta: Optional[float] = None
        wb = _metric(baseline_whole, "loss"); wc = _metric(candidate_whole, "loss")
        if wb is not None and wc is not None:
            whole_delta = wb - wc
            if whole_delta < -self.max_whole_regression:
                reasons.append("whole_piece_regression")

        spill = 0.0
        if adjacent_baseline and adjacent_candidate:
            shared = set(adjacent_baseline) & set(adjacent_candidate)
            regressions = [max(0.0, float(adjacent_candidate[k]) - float(adjacent_baseline[k])) for k in shared]
            spill = max(regressions, default=0.0)
            if spill > self.max_adjacent_regression:
                reasons.append("adjacent_phrase_spillover")

        if len(changed) > self.max_changed_dimensions:
            warnings.append("broad_intervention")

        # Causal confidence is a transparent conservative score, not a probability.
        gain_term = max(0.0, min(1.0, local_delta / max(0.01, abs(b) * 0.25)))
        minimality = max(0.0, 1.0 - max(0, len(changed) - 1) / 8.0)
        spill_term = max(0.0, 1.0 - spill / max(1e-9, self.max_adjacent_regression or 1.0))
        whole_term = 1.0 if whole_delta is None or whole_delta >= 0 else max(0.0, 1.0 + whole_delta / max(1e-9, self.max_whole_regression or 1.0))
        confidence = max(0.0, min(1.0, 0.45 * gain_term + 0.20 * minimality + 0.20 * spill_term + 0.15 * whole_term))
        accepted = not reasons
        return AuditResult(accepted, confidence, local_delta, whole_delta, spill, reasons, warnings, changed)
