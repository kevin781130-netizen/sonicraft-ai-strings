from __future__ import annotations
import json
from pathlib import Path

V20_CURRICULUM='lane_locked_acoustic_promotion_v20'
V19_CURRICULUM='lane_locked_quality_coverage_forge_v19'
CANDIDATE_TOKEN='CANDIDATE_V20'

def promotion_binding(path: str|None):
    """Return (promotion_id, curriculum).

    Candidate training happens before listening evidence exists, so CANDIDATE_V20
    selects the v2.0 lane-locked curriculum without pretending promotion already passed.
    After ABX/tournament, seal_checkpoint_promotion.py adds the immutable promotion ID
    without touching model tensors.
    """
    if not path:return None,V19_CURRICULUM
    if str(path).strip().upper()==CANDIDATE_TOKEN:return None,V20_CURRICULUM
    p=Path(path)
    try:r=json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:raise RuntimeError(f'invalid acoustic promotion report: {p}: {e}') from e
    pid=str(r.get('promotion_id',''))
    if int(r.get('schema',0))!=1 or r.get('promotion_version')!='acoustic_promotion_v20' or not r.get('promotion_pass') or len(pid)!=64:
        raise RuntimeError('acoustic promotion report has not passed v2.0 contract')
    return pid,V20_CURRICULUM
