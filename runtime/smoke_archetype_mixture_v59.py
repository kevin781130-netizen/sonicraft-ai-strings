from pathlib import Path
import tempfile

from archetype_mixture_v59 import (
    mixture_from_distances_v59,ArchetypeMixtureMemoryV59,
    collect_mixture_evidence_v59,predict_candidate_utility_v59,learn_mixture_rendered_v59
)
from performance_archetype_memory_v58 import PerformanceArchetypeMemoryV58
from candidate_utility_predictor_v55 import CandidateUtilityMemoryV55
from context_similarity_transfer_v57 import SimilarityTransferMemoryV57
from counterfactual_auditor_v56 import CounterfactualAuditMemoryV56

features={"dynamic":.49,"contrast":.24,"vibrato":.42,"rate":.50,"bow":.47,"desk":.39,"transition":.42,"role_focus":.60}
dist={"intimate":.12,"ballad":.135,"chamber":.225,"cinematic":.36,"dramatic":.43}
mix=mixture_from_distances_v59(features,dist,.36)
assert mix.confidence>=.42,mix.as_dict()
assert len(mix.components)>=2,mix.as_dict()
assert mix.components[0].label=="intimate"
assert mix.components[1].label=="ballad"
assert abs(sum(c.weight for c in mix.components)-1.0)<2e-6
assert mix.components[0].weight<.8 and mix.components[1].weight>.2,mix.as_dict()

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    um=CandidateUtilityMemoryV55(td/"utility.json")
    am=CounterfactualAuditMemoryV56(td/"audit.json")
    tm=SimilarityTransferMemoryV57(td/"transfer.json")
    arm=PerformanceArchetypeMemoryV58(td/"arch.json")
    mm=ArchetypeMixtureMemoryV59(td/"mix.json")
    key="resolution|transition+vibrato"
    scoresA={"A":{"overall":.91,"safety":.94},"B":{"overall":.80,"safety":.91},
             "C":{"overall":.55,"safety":.82},"D":{"overall":.72,"safety":.95}}
    scoresB={"A":{"overall":.86,"safety":.93},"B":{"overall":.84,"safety":.92},
             "C":{"overall":.58,"safety":.84},"D":{"overall":.72,"safety":.95}}
    # Populate old v5.8 aggregate memory independently for both components.
    for _ in range(12):
        arm.learn_rendered("intimate",key,scoresA,"A",.82,True)
        arm.learn_rendered("ballad",key,scoresB,"A",.82,True)

    pred=predict_candidate_utility_v59(
        "resolution",["transition","vibrato"],{"A":76,"B":73,"C":67},{},{},
        um,am,tm,arm,mm,mix,["A","B","D"]
    )
    assert pred.local_evidence==0
    assert pred.transfer_evidence==0
    assert pred.mixture_evidence>=1.5,pred.as_dict()
    assert pred.reason=="soft_archetype_mixture_top2_plus_D",pred.as_dict()
    assert len(pred.initial_slots)==3 and "D" in pred.initial_slots,pred.as_dict()
    assert pred.confidence<.72,pred.as_dict()  # mixture-only cannot reach Top1+D

    # Weighted learning: only rendered A+D change, skipped B/C do not.
    before={
        lab:{s:float(arm.context(lab,key).get("slots",{}).get(s,{}).get("evidence",0))
             for s in "ABCD"}
        for lab in ("intimate","ballad")
    }
    lr=learn_mixture_rendered_v59(arm,mix,key,{"A":scoresA["A"],"D":scoresA["D"]},"A",False)
    assert lr["learned"]
    after={
        lab:{s:float(arm.context(lab,key).get("slots",{}).get(s,{}).get("evidence",0))
             for s in "ABCD"}
        for lab in ("intimate","ballad")
    }
    for lab in ("intimate","ballad"):
        assert after[lab]["A"]>before[lab]["A"]
        assert after[lab]["D"]>before[lab]["D"]
        assert after[lab]["B"]==before[lab]["B"]
        assert after[lab]["C"]==before[lab]["C"]

    # False prune only calibrates mixture component edges.
    v58_before={lab:arm.calibration(lab,key).copy() for lab in ("intimate","ballad")}
    donor_edges_before=dict(tm.edges)
    ar=mm.record_audit(key,[{"label":c.label,"weight":c.weight} for c in mix.components],
                       {"false_prune":True,"counterfactual_gain":.06})
    assert ar["recorded"]
    trusts={x["label"]:x["trust"] for x in ar["components"]}
    assert trusts["intimate"]<1.0 and trusts["ballad"]<1.0
    assert arm.calibration("intimate",key)==v58_before["intimate"]
    assert arm.calibration("ballad",key)==v58_before["ballad"]
    assert tm.edges==donor_edges_before
    print("SONICRAFT v5.9 soft mixture / weighted learning / isolated audit smoke OK",
          [(c.label,c.weight) for c in mix.components],
          "confidence",mix.confidence,"initial",pred.initial_slots,"trusts",trusts)
