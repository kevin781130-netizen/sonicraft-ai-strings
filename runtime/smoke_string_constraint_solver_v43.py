from score_expression_graph_v40 import ScoreGraph,ScoreNote
from string_physical_graph_v42 import plan_string_physics
from string_constraint_solver_v43 import solve_string_constraints

g=ScoreGraph(tempos=[{"tick":0,"bpm":144.0}])
# Lane 0: long connected legato phrase intended to exceed one bow budget.
tick=0
for i,p in enumerate([55,62,69,76,81,88]):
    g.notes.append(ScoreNote(0,tick,tick+1920,p,base_art=1,stack=2,slur=True,lane_channel=0,source_id=f"L{i}"))
    tick += 1920
# Five-note simultaneous Vln II density > 4.
for i,p in enumerate([55,59,62,66,69]):
    g.notes.append(ScoreNote(1,0,960,p,lane_channel=[1,7,8,9,1][i],source_id=f"C{i}"))
# Out-of-range cello.
g.notes.append(ScoreNote(3,0,960,96,lane_channel=3,source_id="BAD"))

plan_string_physics(g)
g,r=solve_string_constraints(g)
assert r.forced_bow_changes>=1,r.as_dict()
assert r.unplayable_notes>=2,r.as_dict()  # 1 excess density + 1 cello range
assert any(x.kind=="voice_density_exceeds_4x4_bus" for x in r.issues)
assert any(x.kind=="configured_range_violation" for x in r.issues)
assert any("bow_budget_forced_change" in n.constraint_flags for n in g.notes)
assert any(n.playability_risk>=1 for n in g.notes if n.source_id=="BAD")
assert any(x["divisi_required"] for x in r.simultaneous_groups)
# Explicit repair test: poison the second note with a needlessly costly string/finger choice.
rg=ScoreGraph(tempos=[{"tick":0,"bpm":120.0}])
rg.notes=[
    ScoreNote(0,0,960,76,lane_channel=0,source_id="R0"),
    ScoreNote(0,960,1920,71,lane_channel=0,source_id="R1"),
]
plan_string_physics(rg)
rg.notes[0].string_index=3;rg.notes[0].string_name="E";rg.notes[0].finger_semitone=0;rg.notes[0].position_index=0
rg.notes[1].string_index=0;rg.notes[1].string_name="G";rg.notes[1].finger_semitone=16;rg.notes[1].position_index=4
rg,rrep=solve_string_constraints(rg)
assert rrep.repaired_transitions>=1,(rg.notes[1].string_name,rg.notes[1].finger_semitone,rrep.as_dict())
assert "transition_repaired" in rg.notes[1].constraint_flags

print("SONICRAFT v4.3 constraint solver smoke OK",rrep.repaired_transitions,r.forced_bow_changes,r.unplayable_notes,round(r.max_risk,3))
