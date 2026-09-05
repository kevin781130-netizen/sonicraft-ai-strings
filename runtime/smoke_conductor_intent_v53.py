from copy import deepcopy
from score_expression_graph_v40 import ScoreGraph,ScoreNote
from conductor_intent_v53 import build_conductor_intent_v53,evaluate_conductor_intent_v53,choose_conductor_locked_decisions_v53

PPQ=960
def mk(part,start,end,pitch,sid,pid,dyn,vib,rate,pressure,reserve,role):
    n=ScoreNote(part,start,end,pitch,base_art=1,stack=2,slur=True,lane_channel=part,source_id=sid)
    n.phrase_longline_id=pid;n.phrase_vibrato_rate_hz=rate;n.bow_pressure=pressure;n.phrase_bow_reserve=reserve
    n.ensemble_role=role;n.ensemble_attack_offset_ms=(-1.0+part*.65)
    n.transition_in_link_id=pid if sid.endswith("B") else 0
    n.transition_continuity=.68 if n.transition_in_link_id else 0.
    n.transition_duration_ms=62 if n.transition_in_link_id else 0.
    n.gesture_anchors=[
        {"u":0.0,"dynamics_energy":dyn-.025,"vibrato_depth":vib-.02},
        {"u":.5,"dynamics_energy":dyn+.025,"vibrato_depth":vib+.01},
        {"u":1.0,"dynamics_energy":dyn,"vibrato_depth":vib},
    ]
    return n

# 5 macro sections: intro -> build -> sustain -> climax -> resolution.
g=ScoreGraph()
section_dyn=[.48,.58,.64,.82,.56]
section_vib=[.34,.42,.46,.61,.40]
for si,(dyn,vib) in enumerate(zip(section_dyn,section_vib),1):
    a=(si-1)*4*PPQ
    # Lead Vln I and foundation Cello establish persistent section roles.
    g.notes += [
        mk(0,a,a+2*PPQ,72+si,f"S{si}V1A",si,dyn,vib,4.7+.16*si,.46+.025*si,.62,"lead"),
        mk(0,a+2*PPQ,a+4*PPQ,74+si,f"S{si}V1B",si,dyn+.015,vib+.01,4.75+.16*si,.47+.025*si,.48,"lead"),
        mk(3,a,a+2*PPQ,43+si,f"S{si}CEA",100+si,dyn-.08,max(.1,vib-.10),4.55+.10*si,.50+.018*si,.67,"foundation"),
        mk(3,a+2*PPQ,a+4*PPQ,45+si,f"S{si}CEB",100+si,dyn-.06,max(.1,vib-.08),4.60+.10*si,.51+.018*si,.52,"foundation"),
    ]

intent=build_conductor_intent_v53(g)
assert 3<=len(intent.sections)<=8
assert intent.climax_section_id==4,(intent.climax_section_id,[s.dynamic_mean for s in intent.sections])
assert intent.sections[3].character=="climax"
assert intent.sections[-1].character in ("resolution","release","sustain")
base_report=evaluate_conductor_intent_v53(intent,g)
assert base_report.passed,(base_report.score,base_report.as_dict())

A=deepcopy(g);B=deepcopy(g);C=deepcopy(g)
# Window is section 2. C is local Audio winner but makes the build section louder/more intense
# than the intended climax. B is close in Audio score and follows the long-form envelope.
for n in C.notes:
    if 4*PPQ<=n.start_tick<8*PPQ:
        n.bow_pressure=.88;n.phrase_vibrato_rate_hz=6.25;n.phrase_bow_reserve=.18
        for a in n.gesture_anchors:
            a["dynamics_energy"]=.97;a["vibrato_depth"]=.82
for n in A.notes:
    if 4*PPQ<=n.start_tick<8*PPQ:
        n.bow_pressure=.68;n.phrase_vibrato_rate_hz=5.55
        for a in n.gesture_anchors:
            a["dynamics_energy"]=min(.78,a["dynamics_energy"]+.14)
            a["vibrato_depth"]=min(.63,a["vibrato_depth"]+.12)
for n in B.notes:
    if 4*PPQ<=n.start_tick<8*PPQ:
        n.bow_pressure+=.025;n.phrase_vibrato_rate_hz+=.10
        for a in n.gesture_anchors:
            a["dynamics_energy"]=min(.70,a["dynamics_energy"]+.035)
            a["vibrato_depth"]=min(.55,a["vibrato_depth"]+.025)

decision={
    "window_id":1,"start_tick":4*PPQ,"end_tick":8*PPQ,"phrase_keys":[],
    "winner":"C","margin":.032,"duration_seconds":4.0,
    "scores":{
        "C":{"overall":.910,"safety":.88},
        "B":{"overall":.886,"safety":.91},
        "A":{"overall":.850,"safety":.90},
        "D":{"overall":.835,"safety":.92},
    }
}
chosen,coh,irep,meta=choose_conductor_locked_decisions_v53(g,{"A":A,"B":B,"C":C},[decision],intent)
assert chosen is not None,(coh.as_dict(),irep.as_dict(),meta)
assert chosen[0]["local_winner"]=="C"
assert chosen[0]["winner"]=="B",(chosen,irep.as_dict(),meta)
assert chosen[0]["conductor_override"] is True
assert chosen[0]["conductor_character"] in ("build","sustain")
assert coh.passed and irep.passed
# Direct C merge must fail conductor intent.
from global_performance_coherence_v52 import merge_graph_decisions_v52
mg,_=merge_graph_decisions_v52(g,{"A":A,"B":B,"C":C},[decision])
bad=evaluate_conductor_intent_v53(intent,mg)
assert not bad.passed,bad.as_dict()
assert any("climax_shift" in x or "premature_dynamic_ceiling" in x for x in bad.hard_violations),bad.as_dict()

print("SONICRAFT v5.3 conductor intent smoke OK",
      "sections",[(s.section_id,s.character,round(s.dynamic_mean,3)) for s in intent.sections],
      "climax",intent.climax_section_id,
      "local",chosen[0]["local_winner"],"selected",chosen[0]["winner"],
      "intent_score",irep.score,"searched",meta["searched"])
