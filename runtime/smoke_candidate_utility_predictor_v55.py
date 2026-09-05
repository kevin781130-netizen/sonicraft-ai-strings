from pathlib import Path
import tempfile
from candidate_utility_predictor_v55 import CandidateUtilityMemoryV55,predict_candidate_utility_v55,context_key_v55,should_escalate_v55

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'utility.json';m=CandidateUtilityMemoryV55(p)
    dims=['bow_reserve','gesture_spikes','transition']
    # No history => conservative v5.4 primary budget.
    pr0=predict_candidate_utility_v55('resolution',dims,
        {'A':74,'B':77,'C':72},{},None,m,['A','B','D'])
    assert pr0.reason=='v54_primary_fallback' and pr0.initial_slots==['A','B','D'],pr0

    key=context_key_v55('resolution',dims)
    full={
      'A':{'overall':.91,'safety':.92},'B':{'overall':.72,'safety':.90},
      'C':{'overall':.48,'safety':.82},'D':{'overall':.66,'safety':.93}}
    for _ in range(10):
        r=m.learn_rendered(key,full,'A',full_evidence=True);assert r['learned']
    pr=predict_candidate_utility_v55('resolution',dims,
        {'A':76,'B':75,'C':70},{},None,m,['A','B','D'])
    assert pr.confidence>=.72,pr
    assert pr.ranking[0]=='A',pr
    assert pr.initial_slots==['A','D'],pr
    assert set(pr.pruned_slots)=={'B','C'},pr

    # Skipped slots do not receive fake evidence.
    before=m.snapshot()['contexts'][key]['slots']
    ev_a=before['A']['evidence'];ev_b=before['B']['evidence'];ev_c=before['C']['evidence']
    m.learn_rendered(key,{'A':full['A'],'D':full['D']},'A',full_evidence=False)
    after=m.snapshot()['contexts'][key]['slots']
    assert after['B']['evidence']==ev_b and after['C']['evidence']==ev_c
    assert after['A']['evidence']>ev_a

    # Predictor/audio disagreement forces expansion even with healthy Audio margin.
    esc,reason=should_escalate_v55(pr,{'A':{'overall':.70,'safety':.9},'D':{'overall':.86,'safety':.9}},'D',.16)
    assert esc and reason=='predictor_audio_disagreement',(esc,reason)
    esc2,reason2=should_escalate_v55(pr,{'A':{'overall':.90,'safety':.9},'D':{'overall':.68,'safety':.9}},'A',.22)
    assert not esc2 and reason2=='accepted_initial_budget'
    print('SONICRAFT v5.5 Candidate Utility Predictor memory/prune/escalation smoke OK',pr.as_dict())
