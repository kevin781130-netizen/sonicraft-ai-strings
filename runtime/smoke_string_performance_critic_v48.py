from score_expression_graph_v40 import ScoreGraph,ScoreNote
from string_physical_graph_v42 import plan_string_physics
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble
from string_gesture_graph_v45 import plan_continuous_string_gestures
from string_transition_graph_v46 import build_continuous_transition_graph_v46
from string_phrase_longline_v47 import plan_phrase_longlines_v47
from string_performance_critic_v48 import evaluate_performance_v48,generate_repairs_v48

g=ScoreGraph(tempos=[{"tick":0,"bpm":92.0}])
g.notes=[
 ScoreNote(0,0,960,69,base_art=1,stack=2,slur=True,lane_channel=0,source_id="A"),
 ScoreNote(0,960,1920,76,base_art=2,stack=2,slur=True,lane_channel=0,source_id="B"),
 ScoreNote(0,1920,2880,81,base_art=1,stack=2,slur=True,lane_channel=0,source_id="C"),
 ScoreNote(0,2880,3840,74,base_art=1,stack=2,slur=True,lane_channel=0,source_id="D"),
]
plan_string_physics(g);g,_=solve_string_constraints(g);g,_=coordinate_string_ensemble(g)
g=plan_continuous_string_gestures(g);g,_=build_continuous_transition_graph_v46(g);g,_=plan_phrase_longlines_v47(g)

# Poison structurally without changing score pitches: critical reserve, harsh risk/continuity,
# gesture spikes, vibrato-rate jumps and ensemble offset spread.
for i,n in enumerate(g.notes):
    n.phrase_bow_reserve=.04 if i>=2 else .12
    n.bow_pressure=.88
    n.transition_risk=.82 if i else 0.
    if i:n.transition_continuity=.12;n.transition_duration_ms=24.
    n.phrase_vibrato_rate_hz=4.5 if i%2==0 else 6.2
    n.ensemble_attack_offset_ms=(-4.5 if i%2==0 else 4.5)
    for j,a in enumerate(n.gesture_anchors):
        a["bow_pressure"]=.95 if (i+j)%2 else .25
        a["contact_point"]=.92 if (i+j)%2 else .18
        a["dynamics_energy"]=.95 if (i+j)%2 else .35
        a["vibrato_depth"]=.85 if (i+j)%2 else .20
        a["micro_pitch_cents"]=12 if (i+j)%2 else -12

before,issues=evaluate_performance_v48(g)
score,issues,cands,reports,best=generate_repairs_v48(g)
assert score.overall==before.overall
assert len(issues)>=4,(score,issues)
assert all(slot in reports for slot in "ABC")
assert max(r.score_after for r in reports.values())>score.overall+4,(score.overall,{k:v.score_after for k,v in reports.items()})
assert reports["A"].strategy=="Conservative"
assert reports["B"].strategy=="Balanced"
assert reports["C"].strategy=="Expressive"
assert best in "ABC"
# D original must remain untouched by repair generation.
assert g.notes[2].phrase_bow_reserve==.04
print("SONICRAFT v4.8 critic/repair smoke OK",score.overall,{k:v.score_after for k,v in reports.items()},"best",best)
