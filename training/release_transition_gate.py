from __future__ import annotations
"""Pure-JSON validation for Schema 8 phrase-transition release evidence."""
from typing import Mapping

RELEASE_SCHEMA = 8
PHRASE_CURRICULUM_VERSION = 'phrase_finetune_index_v1'
TRANSITION_PROMOTION_VERSION = 'transition_promotion_v1'
REQUIRED_RENDERER_ROLES = ('hq', 'compact')


def _sha256_like(value) -> bool:
    s = str(value or '').lower()
    return len(s) == 64 and all(c in '0123456789abcdef' for c in s)


def curriculum_reasons(report: Mapping) -> list[str]:
    reasons = []
    if report.get('version') != PHRASE_CURRICULUM_VERSION:
        reasons.append('phrase_curriculum_version_invalid')
    if not _sha256_like(report.get('output_index_sha256')):
        reasons.append('phrase_curriculum_output_index_sha256_invalid')
    sweep = dict(report.get('curriculum_sweep') or {})
    if not sweep:
        reasons.append('phrase_curriculum_sweep_missing')
        return reasons
    for stage, audit in sweep.items():
        try:
            modeled = float(audit['modeled_probability'])
            phrase_share = float(audit['phrase_share_within_modeled'])
        except Exception:
            reasons.append('phrase_curriculum_stage_invalid_' + str(stage))
            continue
        if abs(modeled - .20) > .015:
            reasons.append('phrase_curriculum_modeled_lane_drift_' + str(stage))
        if not (0.0 < phrase_share <= 1.0):
            reasons.append('phrase_curriculum_share_invalid_' + str(stage))
    return reasons


def promotion_reasons(report: Mapping, role: str) -> list[str]:
    reasons = []
    prefix = str(role) + '_'
    if int(report.get('schema', 0)) != 1 or report.get('promotion_version') != TRANSITION_PROMOTION_VERSION:
        reasons.append(prefix + 'transition_schema_invalid')
    if not report.get('promotion_pass'):
        reasons.append(prefix + 'transition_promotion_failed')
    if not _sha256_like(report.get('promotion_id')):
        reasons.append(prefix + 'transition_promotion_id_invalid')
    if not _sha256_like(report.get('candidate_checkpoint_sha256')):
        reasons.append(prefix + 'candidate_checkpoint_sha256_invalid')
    if not _sha256_like(report.get('heldout_index_sha256')):
        reasons.append(prefix + 'heldout_index_sha256_invalid')
    try:
        if int(report.get('sample_count', 0)) < 48:
            reasons.append(prefix + 'transition_underpowered')
    except Exception:
        reasons.append(prefix + 'transition_sample_count_invalid')
    return reasons


def release_evidence_reasons(curriculum: Mapping, promotions: Mapping[str, Mapping]) -> list[str]:
    reasons = curriculum_reasons(curriculum)
    for role in REQUIRED_RENDERER_ROLES:
        report = promotions.get(role)
        if not isinstance(report, Mapping):
            reasons.append(role + '_transition_evidence_missing')
            continue
        reasons.extend(promotion_reasons(report, role))
    valid = [promotions.get(role) for role in REQUIRED_RENDERER_ROLES if isinstance(promotions.get(role), Mapping)]
    heldout = {str(r.get('heldout_index_sha256', '')).lower() for r in valid if _sha256_like(r.get('heldout_index_sha256'))}
    if len(heldout) > 1:
        reasons.append('renderer_transition_heldout_index_mismatch')
    ids = [str(r.get('promotion_id', '')).lower() for r in valid if _sha256_like(r.get('promotion_id'))]
    if len(ids) == len(REQUIRED_RENDERER_ROLES) and len(set(ids)) != len(ids):
        reasons.append('renderer_transition_promotion_ids_not_checkpoint_specific')
    return reasons


def assert_release_evidence(curriculum: Mapping, promotions: Mapping[str, Mapping]) -> None:
    reasons = release_evidence_reasons(curriculum, promotions)
    if reasons:
        raise ValueError('; '.join(reasons))
