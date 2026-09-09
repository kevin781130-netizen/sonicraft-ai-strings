"""Clean-room governance layer inspired by public architectural ideas in Sonicraft AI Strings.

No Sonicraft source code is bundled or imported.  This package implements generic
candidate steering, evidence ranking, counterfactual auditing, and provenance using
StringCC's own data model and MIT-licensed codebase.
"""
from .models import ConductorIntent, CandidateProposal, AuditResult
from .conductor import ConductorSteerer
from .utility import CandidateUtilityPredictor
from .audit import CounterfactualAuditor
from .evidence import EvidenceLedger
from .orchestrator import GovernedRepairOrchestrator

__all__ = [
    "ConductorIntent", "CandidateProposal", "AuditResult", "ConductorSteerer",
    "CandidateUtilityPredictor", "CounterfactualAuditor", "EvidenceLedger",
    "GovernedRepairOrchestrator",
]
