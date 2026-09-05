from score_expression_graph_v40 import ScoreGraph,ScoreNote
from string_physical_graph_v42 import plan_string_physics
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble

g=ScoreGraph(tempos=[{"tick":0,"bpm":120.0}])
# Tutti phrase attack. Vln I explicitly forces down; others unforced should follow.
g.notes=[
 ScoreNote(0,0,960,76,base_art=4,stack=1,lane_channel=0,source_id="V1a",technical=["down-bow"]),
 ScoreNote(1,0,960,69,base_art=4,stack=1,lane_channel=1,source_id="V2a"),
 ScoreNote(2,0,960,62,base_art=4,stack=1,lane_channel=2,source_id="Vaa"),
 ScoreNote(3,0,960,50,base_art=4,stack=1,lane_channel=3,source_id="Vca"),
 # phrase endings after a short second note
 ScoreNote(0,960,1440,78,base_art=0,lane_channel=0,source_id="V1b"),
 ScoreNote(1,960,1440,71,base_art=0,lane_channel=1,source_id="V2b"),
 ScoreNote(2,960,1440,64,base_art=0,lane_channel=2,source_id="Vab"),
 ScoreNote(3,960,1440,52,base_art=0,lane_channel=3,source_id="Vcb"),
]
plan_string_physics(g);g,_=solve_string_constraints(g);g,r=coordinate_string_ensemble(g)
first=[n for n in g.notes if n.start_tick==0]
assert len({n.ensemble_group_id for n in first})==1
assert all(n.bow_direction==0 for n in first)
assert all(n.ensemble_bow_sync for n in first)
assert len({round(n.ensemble_attack_offset_ms,3) for n in first})==4
assert max(abs(n.ensemble_attack_offset_ms) for n in first)<=8
ends=[n for n in g.notes if n.start_tick==960]
assert all(n.ensemble_breath_ms>0 for n in ends)
assert r.coordinated_attacks>=8 and r.phrase_breaths>=4

# Explicit conflict must be preserved/reported rather than overwritten.
h=ScoreGraph(tempos=[{"tick":0,"bpm":100.0}])
h.notes=[
 ScoreNote(0,0,960,76,lane_channel=0,source_id="A",technical=["down-bow"]),
 ScoreNote(1,0,960,69,lane_channel=1,source_id="B",technical=["up-bow"]),
]
plan_string_physics(h);h,_=solve_string_constraints(h);h,hr=coordinate_string_ensemble(h)
assert hr.bow_conflicts==1
assert h.notes[0].bow_direction==0 and h.notes[1].bow_direction==1
assert any(x.kind=="explicit_bow_direction_conflict" for x in hr.issues)
print("SONICRAFT v4.4 ensemble solver smoke OK",r.coordinated_attacks,r.coordinated_bow_directions,r.phrase_breaths,hr.bow_conflicts)
