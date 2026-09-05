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


# All three repairs lift the entire pre-climax arc together. v5.2 baseline-relative coherence
# still passes because phrase-to-phrase continuity remains smooth, but v5.3 must reject the
# macro-direction reversal / premature climax.
A=deepcopy(g);B=deepcopy(g);C=deepcopy(g)
for gg in (A,B,C):
    for n in gg.notes:
        if 0<=n.start_tick<12*PPQ:
            n.bow_pressure=min(.92,n.bow_pressure+.24*.28)
            n.phrase_vibrato_rate_hz+=.24*.7
            for a in n.gesture_anchors:
                a["dynamics_energy"]=min(1.0,a["dynamics_energy"]+.24)
                a["vibrato_depth"]=min(1.0,a["vibrato_depth"]+.24*.35)

decision={
    "window_id":1,"start_tick":0,"end_tick":12*PPQ,"phrase_keys":[],
    "winner":"C","margin":.04,"duration_seconds":12.0,
    "scores":{
        "C":{"overall":.92,"safety":.90},
        "B":{"overall":.90,"safety":.90},
        "A":{"overall":.89,"safety":.90},
        "D":{"overall":.20,"safety":.20},
    }
}
chosen,coh,irep,meta=choose_conductor_locked_decisions_v53(g,{"A":A,"B":B,"C":C},[decision],intent)
assert chosen is None,(chosen,coh.as_dict(),irep.as_dict(),meta)
assert meta["reason"]=="no_conductor_locked_candidate_combination"
assert meta["coherence_passed"]>=1,meta
assert meta["intent_passed"]==0,meta
assert coh.passed,coh.as_dict()
assert not irep.passed
assert any("climax_shift" in x or "long_line_direction_reversal" in x for x in irep.hard_violations),irep.as_dict()
print("SONICRAFT v5.3 coherence-PASS / conductor-FAIL fallback smoke OK",
      "searched",meta["searched"],"coherence_passed",meta["coherence_passed"],
      "intent_passed",meta["intent_passed"],"hard",irep.hard_violations)
