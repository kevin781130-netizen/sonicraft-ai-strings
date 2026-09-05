from pathlib import Path
import tempfile
from candidate_utility_predictor_v55 import UtilityPredictionV55
from counterfactual_auditor_v56 import CounterfactualAuditMemoryV56

pred=UtilityPredictionV55(
    'resolution|bow_reserve+transition','resolution',['bow_reserve','transition'],
    {'A':.60,'B':.88,'C':.40,'D':.62},['B','D','A','C'],.91,.26,8.0,
    ['B','D'],['A','C'],'high_conf_top1_plus_D')

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'audit.json';m=CounterfactualAuditMemoryV56(p)
    # Stable context: audit exactly on the 12th prune opportunity.
    for i in range(1,12):
        ap=m.plan(pred,['A','B','D'])
        assert not ap.audit_due,(i,ap)
        assert ap.initial_slots==['B','D'],ap
    ap=m.plan(pred,['A','B','D'])
    assert ap.audit_due and set(ap.audit_slots)=={'A','C'},ap
    assert ap.audit_interval==12 and ap.prune_opportunity==12

    pre={'B':{'overall':.90,'safety':.92},'D':{'overall':.64,'safety':.93}}
    full={'A':{'overall':.96,'safety':.91},'B':pre['B'],'C':{'overall':.58,'safety':.88},'D':pre['D']}
    r=m.record_audit(pred.context_key,pre,'B',full,'A',['A','C'])
    assert r['false_prune'] and abs(r['counterfactual_gain']-.06)<1e-9,r
    assert not r['disabled']

    # Four recent audits with two false prunes => disable predictor Zero-Render for this context.
    clean={'A':{'overall':.70,'safety':.90},'B':{'overall':.91,'safety':.92},'C':{'overall':.61,'safety':.90},'D':{'overall':.65,'safety':.93}}
    m.record_audit(pred.context_key,pre,'B',clean,'B',['A','C'])
    m.record_audit(pred.context_key,pre,'B',full,'A',['A','C'])
    rr=m.record_audit(pred.context_key,pre,'B',clean,'B',['A','C'])
    cal=m.calibration(pred.context_key)
    assert cal['disabled'],cal
    assert cal['audit_interval']==1,cal
    assert cal['confidence_multiplier']<1.0,cal

    # Disabled context falls back to v5.4 budget and audits every opportunity.
    dp=m.plan(pred,['A','B','D'])
    assert not dp.pruning_allowed and dp.audit_due,dp
    assert dp.initial_slots==['A','B','D'],dp
    assert dp.audit_slots==['C'],dp

    # Four clean audits recover the context. Full evidence is assumed in these audit records.
    for _ in range(4):
        m.record_audit(pred.context_key,pre,'B',clean,'B',['A','C'])
    cal2=m.calibration(pred.context_key)
    assert not cal2['disabled'],cal2
    assert cal2['recent_false_prune_rate']<.25,cal2
    m2=CounterfactualAuditMemoryV56(p)
    assert m2.snapshot()==m.snapshot()
    print('SONICRAFT v5.6 Counterfactual Auditor interval/false-prune/disable/recovery smoke OK',cal2)
