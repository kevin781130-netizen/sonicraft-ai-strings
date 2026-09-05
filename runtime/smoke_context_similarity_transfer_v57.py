from pathlib import Path
import tempfile
from candidate_utility_predictor_v55 import CandidateUtilityMemoryV55,context_key_v55
from counterfactual_auditor_v56 import CounterfactualAuditMemoryV56
from context_similarity_transfer_v57 import SimilarityTransferMemoryV57,predict_candidate_utility_v57,context_similarity_v57

SCORE_A={"overall":.86,"safety":.90};SCORE_B={"overall":.78,"safety":.90};SCORE_C={"overall":.62,"safety":.86};SCORE_D={"overall":.60,"safety":.92}
with tempfile.TemporaryDirectory() as td:
    td=Path(td);um=CandidateUtilityMemoryV55(td/'utility.json');am=CounterfactualAuditMemoryV56(td/'audit.json');tm=SimilarityTransferMemoryV57(td/'transfer.json')
    k_t=context_key_v55('resolution',['transition','vibrato'])
    k1=context_key_v55('resolution',['transition'])
    k2=context_key_v55('resolution',['vibrato'])
    k_bad_char=context_key_v55('climax',['transition','vibrato'])
    k_bad_dim=context_key_v55('resolution',['ensemble_alignment'])
    assert context_similarity_v57(k_t,k1)>.5
    assert context_similarity_v57(k_t,k_bad_char)==0
    assert context_similarity_v57(k_t,k_bad_dim)==0
    for _ in range(12):
        um.learn_rendered(k1,{'A':SCORE_A,'B':SCORE_B,'C':SCORE_C,'D':SCORE_D},'A',True)
        um.learn_rendered(k2,{'A':SCORE_A,'B':SCORE_B,'C':SCORE_C,'D':SCORE_D},'A',True)
        um.learn_rendered(k_bad_char,{'C':SCORE_A,'B':SCORE_B,'A':SCORE_C,'D':SCORE_D},'C',True)
        um.learn_rendered(k_bad_dim,{'B':SCORE_A,'A':SCORE_B,'C':SCORE_C,'D':SCORE_D},'B',True)
    p=predict_candidate_utility_v57('resolution',['transition','vibrato'],
        steered_scores={'A':78,'B':73,'C':64},repair_reports={},policy={},
        utility_memory=um,audit_memory=am,transfer_memory=tm,v54_primary=['A','B','D'])
    assert p.local_evidence==0,p
    assert p.transfer_evidence>=1.5,p
    assert p.reason=='similarity_transfer_top2_plus_D',p
    assert len(p.initial_slots)==3 and 'D' in p.initial_slots,p.initial_slots
    assert p.confidence<.72,p.confidence # transfer-only may never unlock Top1+D
    assert k1 in p.transfer_donors and k2 in p.transfer_donors,p.transfer_donors
    assert k_bad_char not in p.transfer_donors and k_bad_dim not in p.transfer_donors

    # Two false + two clean audits disable only the k_t<-k1 edge; donor k1 local memory is untouched.
    ev_before=um.context(k1)['slots']['A']['evidence']
    false={'false_prune':True,'counterfactual_gain':.06}
    clean={'false_prune':False,'counterfactual_gain':0.0}
    tm.record_audit(k_t,[k1],false);tm.record_audit(k_t,[k1],false)
    tm.record_audit(k_t,[k1],clean);r=tm.record_audit(k_t,[k1],clean)
    assert tm.calibration(k_t,k1)['disabled'] is True,tm.calibration(k_t,k1)
    assert um.context(k1)['slots']['A']['evidence']==ev_before
    p2=predict_candidate_utility_v57('resolution',['transition','vibrato'],
        steered_scores={'A':78,'B':73,'C':64},repair_reports={},policy={},
        utility_memory=um,audit_memory=am,transfer_memory=tm,v54_primary=['A','B','D'])
    assert k1 not in p2.transfer_donors and k2 in p2.transfer_donors,p2.transfer_donors
    print('SONICRAFT v5.7 similarity transfer / edge isolation smoke OK',
          'transfer_evidence',p.transfer_evidence,'confidence',p.confidence,
          'initial',p.initial_slots,'edge_disabled',tm.calibration(k_t,k1)['disabled'])
