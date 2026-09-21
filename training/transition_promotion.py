from __future__ import annotations
"""Promotion contract for clean-room phrase/transition fine-tuning."""
from typing import Mapping
import hashlib, json

SCHEMA=1
VERSION='transition_promotion_v1'


def _canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def _id(*parts): return hashlib.sha256(b'|'.join(_canonical(x) for x in parts)).hexdigest()


def build_transition_promotion(
    baseline: Mapping,
    candidate: Mapping,
    curriculum: Mapping,
    *,
    min_samples: int = 48,
    max_continuity_ratio: float = .99,
    max_accel_ratio: float = 1.02,
    max_flow_ratio: float = 1.03,
    max_composite_ratio: float = .995,
):
    reasons=[]
    for label,r in (('baseline',baseline),('candidate',candidate)):
        if int(r.get('schema',0))!=1 or r.get('version')!='renderer_transition_eval_v1': reasons.append(label+'_schema_invalid')
        if int(r.get('sample_count',0))<int(min_samples): reasons.append(label+'_underpowered')
    if baseline.get('index_sha256')!=candidate.get('index_sha256'): reasons.append('heldout_index_mismatch')
    if baseline.get('seed')!=candidate.get('seed'): reasons.append('paired_seed_mismatch')

    b=dict(baseline.get('metrics') or {}); c=dict(candidate.get('metrics') or {})
    ratios={}
    for k in ('flow','continuity','accel'):
        try: ratios[k]=float(c[k])/max(float(b[k]),1e-12)
        except Exception: reasons.append('missing_metric_'+k); ratios[k]=float('inf')
    composite=.15*ratios['flow']+.55*ratios['continuity']+.30*ratios['accel']
    if ratios['continuity']>max_continuity_ratio: reasons.append('continuity_not_improved')
    if ratios['accel']>max_accel_ratio: reasons.append('acceleration_regressed')
    if ratios['flow']>max_flow_ratio: reasons.append('heldout_flow_regressed')
    if composite>max_composite_ratio: reasons.append('transition_composite_failed')

    sweep=dict(curriculum.get('curriculum_sweep') or {})
    if not sweep: reasons.append('curriculum_audit_missing')
    for stage,audit in sweep.items():
        try:
            modeled=float(audit['modeled_probability']); phrase_share=float(audit['phrase_share_within_modeled'])
            if abs(modeled-.20)>.015: reasons.append('modeled_lane_drift_'+str(stage))
            if phrase_share<=0: reasons.append('phrase_sampling_missing_'+str(stage))
        except Exception: reasons.append('curriculum_stage_invalid_'+str(stage))

    pid=_id(baseline,candidate,curriculum,{
        'min_samples':min_samples,'max_continuity_ratio':max_continuity_ratio,'max_accel_ratio':max_accel_ratio,
        'max_flow_ratio':max_flow_ratio,'max_composite_ratio':max_composite_ratio,
    })
    return {
        'schema':SCHEMA,'promotion_version':VERSION,'promotion_id':pid,'promotion_pass':not reasons,
        'baseline_checkpoint_sha256':baseline.get('checkpoint_sha256'),'candidate_checkpoint_sha256':candidate.get('checkpoint_sha256'),
        'heldout_index_sha256':candidate.get('index_sha256'),'sample_count':candidate.get('sample_count'),
        'ratios':ratios,'composite_ratio':composite,
        'thresholds':{'continuity':max_continuity_ratio,'accel':max_accel_ratio,'flow':max_flow_ratio,'composite':max_composite_ratio},
        'reasons':reasons,
        'contract':'phrase fine-tune must improve continuity, avoid acceleration/flow regression, and keep clean-room phrases inside the MODELED lane',
    }
