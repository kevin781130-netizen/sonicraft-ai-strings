from score_expression_graph_v40 import ScoreGraph,ScoreNote
from string_physical_graph_v42 import plan_string_physics
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble
from string_gesture_graph_v45 import plan_continuous_string_gestures

g=ScoreGraph(tempos=[{'tick':0,'bpm':80.0}]);g.notes=[
 ScoreNote(0,0,3840,76,base_art=3,stack=8,cc1=82,cc3=88,lane_channel=0,source_id='LONG'),
 ScoreNote(0,3840,4800,78,base_art=2,stack=2,cc1=78,cc3=64,lane_channel=0,source_id='PORT'),
 ScoreNote(1,0,960,69,base_art=8,cc1=80,cc3=0,lane_channel=1,source_id='PIZZ')]
plan_string_physics(g);g,_=solve_string_constraints(g);g,_=coordinate_string_ensemble(g);plan_continuous_string_gestures(g)
a,b,p=g.notes
assert a.gesture_profile=='expressive-swell' and len(a.gesture_anchors)==7 and a.gesture_amount==1.0
assert max(x['dynamics_energy'] for x in a.gesture_anchors)>min(x['dynamics_energy'] for x in a.gesture_anchors)
assert all(-14<=x['micro_pitch_cents']<=14 for x in a.gesture_anchors)
assert b.gesture_profile=='portamento-arc' and b.gesture_anchors[-1]['portamento']>b.gesture_anchors[0]['portamento']
assert p.gesture_amount==0 and not p.gesture_anchors
print('SONICRAFT v4.5 gesture graph smoke OK')
