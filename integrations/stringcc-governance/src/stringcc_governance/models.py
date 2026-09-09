from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import hashlib
import json


def stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:16]}"


@dataclass(frozen=True)
class ConductorIntent:
    """Global performance intent used to bias phrase-local candidate generation."""
    energy: float = 0.5
    tension: float = 0.5
    continuity: float = 0.7
    contrast: float = 0.4
    vibrato_character: float = 0.5
    bow_weight: float = 0.5
    restraint: float = 0.5
    section_role: str = "support"  # lead, support, transition, cadence

    def clamped(self) -> "ConductorIntent":
        vals = {k: max(0.0, min(1.0, float(getattr(self, k)))) for k in (
            "energy", "tension", "continuity", "contrast", "vibrato_character", "bow_weight", "restraint"
        )}
        vals["section_role"] = str(self.section_role)
        return ConductorIntent(**vals)


@dataclass
class CandidateProposal:
    phrase_key: str
    family: str
    overrides: dict[str, float]
    expected_effect: str
    changed_dimensions: list[str]
    parent_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    candidate_id: str = ""

    def __post_init__(self) -> None:
        if not self.candidate_id:
            self.candidate_id = stable_id("cand", {
                "phrase_key": self.phrase_key,
                "family": self.family,
                "overrides": self.overrides,
                "parent_id": self.parent_id,
            })

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditResult:
    accepted: bool
    causal_confidence: float
    local_delta: float
    whole_delta: Optional[float]
    spillover: float
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    changed_dimensions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
