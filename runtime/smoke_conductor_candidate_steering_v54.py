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


from string_performance_critic_v48 import generate_repairs_v48
from conductor_candidate_steering_v54 import steer_candidates_v54,render_slots_for_window_v54

_,_,raw,_,_=generate_repairs_v48(g)
steered,report=steer_candidates_v54(g,raw,intent)

# Progressive render budgets follow section character.
climax=intent.sections[intent.climax_section_id-1]
cp=render_slots_for_window_v54(intent,climax.start_tick,climax.end_tick)
assert cp["character"]=="climax"
assert cp["active"]==["B","C","D"] and cp["deferred"]==["A"],cp

res=intent.sections[-1]
rp=render_slots_for_window_v54(intent,res.start_tick,res.end_tick)
assert rp["character"]=="resolution"
assert rp["active"]==["A","B","D"] and rp["deferred"]==["C"],rp

def mean_dyn(graph,a,b):
    v=[]
    for n in graph.notes:
        if n.start_tick<b and n.end_tick>a:
            v += [float(x["dynamics_energy"]) for x in n.gesture_anchors]
    return sum(v)/len(v)

# At climax the expressive candidate is intentionally above Balanced, but cannot exceed intent ceiling.
a,b=climax.start_tick,climax.end_tick
bd=mean_dyn(steered["B"],a,b);cd=mean_dyn(steered["C"],a,b)
assert cd>bd,(bd,cd)
assert max(float(x["dynamics_energy"]) for n in steered["C"].notes if n.start_tick<b and n.end_tick>a for x in n.gesture_anchors)<=climax.dynamic_ceiling+1e-9

# At resolution Conservative is no hotter than Balanced.
a,b=res.start_tick,res.end_tick
ad=mean_dyn(steered["A"],a,b);bd2=mean_dyn(steered["B"],a,b)
assert ad<=bd2+1e-9,(ad,bd2)

# Immutable musical identity survives steering.
keys=("part","start_tick","end_tick","pitch","velocity","voice","staff","source_id","lane_channel","base_art","stack")
sig=lambda gg:[tuple(getattr(n,k) for k in keys) for n in gg.notes]
for slot in "ABC":assert sig(steered[slot])==sig(g)

assert report.intent_hash==intent.intent_hash
assert len(report.sections)>=3*len(intent.sections)
print("SONICRAFT v5.4 conductor-steered candidate smoke OK",
      "climax B/C",round(bd,4),round(cd,4),
      "resolution A/B",round(ad,4),round(bd2,4),
      "budget",cp,rp)
