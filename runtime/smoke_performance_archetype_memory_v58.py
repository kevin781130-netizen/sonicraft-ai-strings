from types import SimpleNamespace
from pathlib import Path
import tempfile

from performance_archetype_memory_v58 import (
    classify_archetype_v58,PerformanceArchetypeMemoryV58,predict_candidate_utility_v58
)
from candidate_utility_predictor_v55 import CandidateUtilityMemoryV55
from context_similarity_transfer_v57 import SimilarityTransferMemoryV57
from counterfactual_auditor_v56 import CounterfactualAuditMemoryV56

def sec(i,dyn,peak,vib,rate,bow,desk,trans,role=.58):
    return SimpleNamespace(
        section_id=i,start_tick=(i-1)*3840,end_tick=i*3840,character="resolution",
        dynamic_mean=dyn,dynamic_peak=peak,dynamic_ceiling=min(1.0,peak+.05),
        vibrato_depth=vib,vibrato_rate_hz=rate,bow_pressure=bow,bow_reserve_floor=.52,
        desk_looseness_ms=desk,transition_density=trans,transition_treatment=trans,
        part_roles={"0":{"lead":role,"inner":1-role,"foundation":0.0},
                    "3":{"lead":0.0,"inner":1-role,"foundation":role}},
        note_count=8
    )

# Construct an Intimate-like D-derived control envelope.
secs=[
    sec(1,.50,.66,.35,5.10,.50,.90,.31,.60),
    sec(2,.52,.68,.37,5.18,.52,.97,.35,.58),
    sec(3,.535,.69,.36,5.22,.515,.94,.34,.59),
]
intent=SimpleNamespace(sections=secs)
cls=classify_archetype_v58(intent)
assert cls.label=="intimate",cls.as_dict()
assert cls.confidence>=.42,cls.as_dict()

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    um=CandidateUtilityMemoryV55(td/"utility.json")
    am=CounterfactualAuditMemoryV56(td/"audit.json")
    tm=SimilarityTransferMemoryV57(td/"transfer.json")
    arch=PerformanceArchetypeMemoryV58(td/"arch.json")

    key="resolution|transition+vibrato"
    # Cross-song archetype history: only actual rendered evidence is learned.
    scores={
        "A":{"overall":.91,"safety":.94},
        "B":{"overall":.84,"safety":.91},
        "C":{"overall":.56,"safety":.82},
        "D":{"overall":.73,"safety":.95},
    }
    for _ in range(9):
        r=arch.learn_rendered(cls.label,key,scores,"A",cls.confidence,full_evidence=True)
        assert r["learned"]
    # Exact utility and v5.7 similarity memories are intentionally empty.
    pred=predict_candidate_utility_v58(
        "resolution",["transition","vibrato"],
        steered_scores={"A":74,"B":72,"C":68},repair_reports={},policy={},
        utility_memory=um,audit_memory=am,transfer_memory=tm,
        archetype_memory=arch,archetype_classification=cls,
        v54_primary=["A","B","D"]
    )
    assert pred.local_evidence==0
    assert pred.transfer_evidence==0
    assert pred.archetype_evidence>=1.5,pred.as_dict()
    assert pred.reason=="archetype_cross_song_top2_plus_D",pred.as_dict()
    assert len([s for s in pred.initial_slots if s!="D"])==2,pred.as_dict()
    assert "D" in pred.initial_slots
    # Archetype-only evidence is not allowed to unlock Top1+D.
    assert len(pred.initial_slots)>=3,pred.as_dict()
    # Skipped slots are never learned: verify B/C unchanged when only A+D are actually rendered.
    before=arch.context(cls.label,key)["slots"]["B"]["evidence"]
    rr=arch.learn_rendered(cls.label,key,{"A":scores["A"],"D":scores["D"]},"A",cls.confidence,full_evidence=False)
    assert rr["learned"]
    after=arch.context(cls.label,key)["slots"]["B"]["evidence"]
    assert after==before,(before,after)

    # Low-confidence archetype classification cannot borrow even abundant memory.
    low=type(cls)(cls.label,.30,cls.secondary_label,cls.secondary_confidence,cls.features,cls.distances,"low_confidence_control_profile")
    blocked=predict_candidate_utility_v58(
        "build",["transition","vibrato"],
        steered_scores={"A":70,"B":72,"C":74},repair_reports={},policy={},
        utility_memory=CandidateUtilityMemoryV55(td/"empty_utility.json"),
        audit_memory=CounterfactualAuditMemoryV56(td/"empty_audit.json"),
        transfer_memory=SimilarityTransferMemoryV57(td/"empty_transfer.json"),
        archetype_memory=arch,archetype_classification=low,
        v54_primary=["A","B","C","D"]
    )
    assert blocked.archetype_evidence==0,blocked.as_dict()
    assert blocked.archetype_detail["reason"]=="low_archetype_confidence",blocked.as_dict()

    # False-prune audit calibrates only archetype->context trust, not stored slot evidence.
    donor_before=arch.context(cls.label,key)["slots"]["A"]["evidence"]
    audit={"false_prune":True,"counterfactual_gain":.06}
    ar=arch.record_audit(cls.label,key,audit)
    assert ar["recorded"]
    assert ar["calibration"]["trust"]<1.0,ar
    assert arch.context(cls.label,key)["slots"]["A"]["evidence"]==donor_before
    print("SONICRAFT v5.8 archetype cold-start / actual-render-only / audit-isolation smoke OK",
          cls.label,cls.confidence,pred.reason,pred.initial_slots,
          "arch_ev",pred.archetype_evidence,"trust",ar["calibration"]["trust"])
