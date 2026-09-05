from score_expression_graph_v40 import ScoreGraph,ScoreNote
from string_physical_graph_v42 import plan_string_physics
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble
from string_gesture_graph_v45 import plan_continuous_string_gestures
from string_transition_graph_v46 import build_continuous_transition_graph_v46
from string_phrase_longline_v47 import plan_phrase_longlines_v47
from string_performance_critic_v48 import evaluate_performance_v48,generate_repairs_v48
from selective_phrase_search_v51 import build_selective_plan_v51

g=ScoreGraph(tempos=[{"tick":0,"bpm":90.0}])
# Phrase 1: deliberately damaged. Phrase 2: clean and far away.
g.notes=[
 ScoreNote(0,0,960,69,base_art=1,stack=2,slur=True,lane_channel=0,source_id="P1A"),
 ScoreNote(0,960,1920,81,base_art=2,stack=2,slur=True,lane_channel=0,source_id="P1B"),
 ScoreNote(0,1920,2880,74,base_art=1,stack=2,slur=True,lane_channel=0,source_id="P1C"),
 ScoreNote(0,6000,6960,72,base_art=1,stack=2,slur=True,lane_channel=0,source_id="P2A"),
 ScoreNote(0,6960,7920,74,base_art=1,stack=2,slur=True,lane_channel=0,source_id="P2B"),
]
plan_string_physics(g);g,_=solve_string_constraints(g);g,_=coordinate_string_ensemble(g)
g=plan_continuous_string_gestures(g);g,_=build_continuous_transition_graph_v46(g);g,_=plan_phrase_longlines_v47(g)

# Damage only phrase 1 enough for the critic to localize.
for n in g.notes[:3]:
    n.phrase_bow_reserve=.03
    n.transition_risk=.88 if n.transition_in_link_id else 0.
    n.transition_continuity=.08 if n.transition_in_link_id else 0.
    n.transition_duration_ms=22. if n.transition_in_link_id else 0.
    for j,a in enumerate(n.gesture_anchors):
        a["bow_pressure"]=.95 if j%2 else .20
        a["contact_point"]=.90 if j%2 else .18
        a["micro_pitch_cents"]=12 if j%2 else -12

score,issues=evaluate_performance_v48(g)
_,_,_,reports,_=generate_repairs_v48(g)
p=build_selective_plan_v51(g,issues,reports,max_windows=4,coverage_limit=.55)
assert p.selective,p.as_dict()
assert len(p.windows)==1,p.as_dict()
w=p.windows[0]
assert w.end_tick<5000,w
assert p.coverage<.55
assert any(x.startswith("phrase:") for x in w.phrase_keys)
fallback=build_selective_plan_v51(g,issues,reports,max_windows=4,coverage_limit=.20)
assert not fallback.selective and fallback.fallback_reason=="problem_coverage_too_large"
print("SONICRAFT v5.1 selective phrase search + coverage fallback smoke OK",round(p.coverage,3),w.start_tick,w.end_tick,w.dimensions)
