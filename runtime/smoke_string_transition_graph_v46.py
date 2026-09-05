from score_expression_graph_v40 import ScoreGraph,ScoreNote
from string_physical_graph_v42 import plan_string_physics
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble
from string_gesture_graph_v45 import plan_continuous_string_gestures
from string_transition_graph_v46 import build_continuous_transition_graph_v46

g=ScoreGraph(tempos=[{"tick":0,"bpm":92.0}])
g.notes=[
    ScoreNote(0,0,960,69,base_art=1,stack=2,slur=True,lane_channel=0,source_id="A"),
    ScoreNote(0,960,1920,76,base_art=2,stack=2,slur=True,lane_channel=0,source_id="B"),
    ScoreNote(0,2880,3360,77,base_art=5,lane_channel=0,source_id="C"),
]
plan_string_physics(g);g,_=solve_string_constraints(g);g,_=coordinate_string_ensemble(g);g=plan_continuous_string_gestures(g)
before=(g.notes[0].gesture_anchors[-1]["bow_pressure"],g.notes[1].gesture_anchors[0]["bow_pressure"])
g,links=build_continuous_transition_graph_v46(g)
assert len(links)==1,links
a,b,c=g.notes
assert a.transition_out_link_id==b.transition_in_link_id==1
assert a.transition_phrase_continuous and b.transition_phrase_continuous
assert "portamento_path" in b.transition_flags
assert b.transition_duration_ms>=35
assert c.transition_in_link_id==0
assert a.gesture_anchors[-1]["bow_pressure"]==b.gesture_anchors[0]["bow_pressure"]
assert a.gesture_anchors[-1]["contact_point"]==b.gesture_anchors[0]["contact_point"]
assert a.gesture_anchors[-1]["dynamics_energy"]==b.gesture_anchors[0]["dynamics_energy"]
print("SONICRAFT v4.6 transition graph smoke OK",links[0].mode,round(links[0].duration_ms,2),before)
