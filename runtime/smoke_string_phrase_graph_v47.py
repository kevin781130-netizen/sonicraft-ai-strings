from score_expression_graph_v40 import ScoreGraph,ScoreNote
from string_physical_graph_v42 import plan_string_physics
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble
from string_gesture_graph_v45 import plan_continuous_string_gestures
from string_transition_graph_v46 import build_continuous_transition_graph_v46
from string_phrase_longline_v47 import plan_phrase_longlines_v47

g=ScoreGraph(tempos=[{"tick":0,"bpm":90.0}])
g.notes=[
 ScoreNote(0,0,960,69,base_art=1,stack=2,slur=True,lane_channel=0,source_id="A"),
 ScoreNote(0,960,1920,72,base_art=1,stack=2,slur=True,lane_channel=0,source_id="B"),
 ScoreNote(0,1920,2880,76,base_art=2,stack=2,slur=True,lane_channel=0,source_id="C"),
 ScoreNote(0,2880,3840,74,base_art=1,stack=2,slur=True,lane_channel=0,source_id="D"),
]
plan_string_physics(g);g,_=solve_string_constraints(g);g,_=coordinate_string_ensemble(g)
g=plan_continuous_string_gestures(g);g,links=build_continuous_transition_graph_v46(g);g,arcs=plan_phrase_longlines_v47(g)
assert len(links)==3 and len(arcs)==1
assert all(n.phrase_longline_id==1 for n in g.notes)
assert all(n.phrase_longline_enabled for n in g.notes)
assert arcs[0].note_count==4
assert arcs[0].energy_apex>arcs[0].energy_start
assert g.notes[0].gesture_anchors[-1]["dynamics_energy"]!=0
assert any("vibrato_rate_target" in n.phrase_longline_flags for n in g.notes)
print("SONICRAFT v4.7 phrase graph smoke OK",arcs[0].contour,round(arcs[0].energy_apex,3),round(arcs[0].bow_reserve_end,3))
