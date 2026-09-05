from copy import deepcopy
from score_expression_graph_v40 import ScoreGraph,ScoreNote
from global_performance_coherence_v52 import evaluate_global_coherence_v52,choose_coherent_decisions_v52,merge_graph_decisions_v52

def note(start,end,pitch,sid,pid,dyn=.62,vib=.46,rate=5.05,pressure=.50,reserve=.55,offset=-.4,role="lead",trans=False):
    n=ScoreNote(0,start,end,pitch,base_art=1,stack=2,slur=True,lane_channel=0,source_id=sid)
    n.phrase_longline_id=pid;n.phrase_vibrato_rate_hz=rate;n.bow_pressure=pressure;n.phrase_bow_reserve=reserve
    n.ensemble_attack_offset_ms=offset;n.ensemble_role=role
    n.transition_in_link_id=pid if trans else 0;n.transition_continuity=.72 if trans else 0.;n.transition_duration_ms=58 if trans else 0.
    n.gesture_anchors=[
        {"u":0.0,"dynamics_energy":dyn-.02,"vibrato_depth":vib-.02},
        {"u":.5,"dynamics_energy":dyn+.02,"vibrato_depth":vib+.01},
        {"u":1.0,"dynamics_energy":dyn,"vibrato_depth":vib},
    ]
    return n

base=ScoreGraph()
base.notes=[
    note(0,900,69,"P1A",1,dyn=.60,vib=.44,rate=5.00,pressure=.49,reserve=.58),
    note(900,1800,72,"P1B",1,dyn=.63,vib=.47,rate=5.10,pressure=.51,reserve=.46,trans=True),
    note(2400,3300,71,"P2A",2,dyn=.64,vib=.48,rate=5.15,pressure=.52,reserve=.57),
    note(3300,4200,74,"P2B",2,dyn=.66,vib=.50,rate=5.20,pressure=.53,reserve=.45,trans=True),
    note(4800,5700,72,"P3A",3,dyn=.65,vib=.49,rate=5.15,pressure=.52,reserve=.58),
    note(5700,6600,76,"P3B",3,dyn=.67,vib=.51,rate=5.25,pressure=.53,reserve=.46,trans=True),
]

A=deepcopy(base);B=deepcopy(base);C=deepcopy(base)
# A is locally exciting but globally discontinuous in the middle phrase.
for n in A.notes[2:4]:
    n.bow_pressure=.86;n.phrase_bow_reserve=.18;n.phrase_vibrato_rate_hz=6.15;n.ensemble_attack_offset_ms=4.0
    n.transition_continuity=.98;n.transition_duration_ms=130
    for a in n.gesture_anchors:
        a["dynamics_energy"]=min(1.0,a["dynamics_energy"]+.27)
        a["vibrato_depth"]=min(1.0,a["vibrato_depth"]+.25)
# B is a near-scoring candidate that preserves the piece's character.
for n in B.notes[2:4]:
    n.bow_pressure+=.025;n.phrase_vibrato_rate_hz+=.08
    for a in n.gesture_anchors:
        a["dynamics_energy"]=min(1.0,a["dynamics_energy"]+.035)
        a["vibrato_depth"]=min(1.0,a["vibrato_depth"]+.025)
# C is more expressive than B, but still within a moderate range.
for n in C.notes[2:4]:
    n.bow_pressure+=.06;n.phrase_vibrato_rate_hz+=.18
    for a in n.gesture_anchors:
        a["dynamics_energy"]=min(1.0,a["dynamics_energy"]+.075)
        a["vibrato_depth"]=min(1.0,a["vibrato_depth"]+.06)

decision={
    "window_id":1,"start_tick":2400,"end_tick":4200,"phrase_keys":["0:0:P2"],
    "winner":"A","margin":.035,"duration_seconds":2.0,
    "scores":{
        "A":{"overall":.90,"safety":.82},
        "B":{"overall":.875,"safety":.86},
        "C":{"overall":.85,"safety":.84},
        "D":{"overall":.82,"safety":.88},
    }
}
mg,modified=merge_graph_decisions_v52(base,{"A":A,"B":B,"C":C},[decision])
bad=evaluate_global_coherence_v52(base,mg,modified)
assert not bad.passed,(bad.score,bad.max_edge_excess,bad.as_dict())

chosen,rep,meta=choose_coherent_decisions_v52(base,{"A":A,"B":B,"C":C},[decision])
assert chosen is not None,(rep.as_dict(),meta)
assert chosen[0]["local_winner"]=="A"
assert chosen[0]["winner"]=="B",(chosen,rep.as_dict(),meta)
assert chosen[0]["coherence_override"] is True
assert rep.passed
assert meta["overrides"]==1
# D Original must trivially pass coherence.
drep=evaluate_global_coherence_v52(base,base,set())
assert drep.passed and abs(drep.score-100)<1e-6
print("SONICRAFT v5.2 global coherence substitution smoke OK",
      "A_score",bad.score,"selected",chosen[0]["winner"],"coherence",rep.score,"searched",meta["searched"])
