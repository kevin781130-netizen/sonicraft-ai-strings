from pathlib import Path
import tempfile
from candidate_utility_predictor_v55 import CandidateUtilityMemoryV55,context_key_v55
from counterfactual_auditor_v56 import CounterfactualAuditMemoryV56
from context_similarity_transfer_v57 import SimilarityTransferMemoryV57,predict_candidate_utility_v57
with tempfile.TemporaryDirectory() as td:
    td=Path(td);um=CandidateUtilityMemoryV55(td/'u.json');am=CounterfactualAuditMemoryV56(td/'a.json');tm=SimilarityTransferMemoryV57(td/'t.json')
    donor=context_key_v55('build',['transition']);target=context_key_v55('build',['transition','vibrato'])
    hist={'A':{'overall':.70,'safety':.9},'B':{'overall':.93,'safety':.93},'C':{'overall':.60,'safety':.88},'D':{'overall':.64,'safety':.93}}
    for _ in range(12):um.learn_rendered(donor,hist,'B',True)
    pre={'B':{'overall':.80,'safety':.9},'D':{'overall':.60,'safety':.9}}
    full={'A':{'overall':.92,'safety':.9},'B':{'overall':.80,'safety':.9},'C':{'overall':.50,'safety':.9},'D':{'overall':.60,'safety':.9}}
    for _ in range(4):am.record_audit(donor,pre,'B',full,'A',['A','C'])
    assert am.calibration(donor)['disabled'] is True,am.calibration(donor)
    p=predict_candidate_utility_v57('build',['transition','vibrato'],{'A':70,'B':75,'C':68},{},{},um,am,tm,['A','B','C','D'])
    assert p.transfer_evidence==0,p
    assert donor not in p.transfer_donors,p.transfer_detail
    assert p.reason=='v54_primary_fallback',p
    assert p.initial_slots==['A','B','C','D'],p.initial_slots
    print('SONICRAFT v5.7 donor high-risk Audit blocks similarity transfer OK',am.calibration(donor)['recent_false_prune_rate'])
