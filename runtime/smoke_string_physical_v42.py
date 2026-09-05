from __future__ import annotations
import numpy as np
from score_expression_graph_v40 import ScoreGraph,ScoreNote
from string_physical_graph_v42 import plan_string_physics,PHYS_POSITION,PHYS_BOW_CHANGE,PHYS_PORTAMENTO
from string_physical_runtime_v42 import physical_curves,apply_string_physical_residuals

g=ScoreGraph()
# One Vln I lane: short open G, then detached D, then slurred A, then explicit portamento E.
g.notes=[
    ScoreNote(0,0,480,55,base_art=5,lane_channel=0),
    ScoreNote(0,480,960,62,base_art=0,lane_channel=0),
    ScoreNote(0,960,1440,69,base_art=1,stack=2,slur=True,lane_channel=0),
    ScoreNote(0,1440,1920,76,base_art=2,stack=2,slur=True,lane_channel=0),
]
plan_string_physics(g)
n0,n1,n2,n3=g.notes
assert n0.open_string and n0.string_name=="G"
assert all(0<=n.string_index<=3 for n in g.notes)
assert all(n.position_index>=0 for n in g.notes)
assert n0.bow_change
assert n2.portamento_route>=0
assert n3.portamento_route==1.0
assert n3.divisi_desk==0

# Legacy events must not activate the physical layer.
legacy=[{'project_sample':0,'type':1,'note':60,'velocity':.8}]
assert physical_curves(legacy,0,48000,100,100) is None

events=[
 {'project_sample':0,'type':4,'note':113,'velocity':.70},
 {'project_sample':0,'type':4,'note':115,'velocity':1.0},
 {'project_sample':0,'type':4,'note':118,'velocity':.80},
]
phys=physical_curves(events,0,48000,100,100)
assert phys is not None and abs(float(phys[PHYS_POSITION][0])-.70)<1e-6
dyn=np.full(100,.6,np.float32);vib=np.full(100,.5,np.float32);exp=np.full(100,.9,np.float32)
leg=np.zeros(100,np.float32);trans=np.full(100,.5,np.float32);tight=np.full(100,.5,np.float32)
attack=np.full(100,.4,np.float32);bow=np.zeros(100,np.float32);pb=np.full(100,.5,np.float32)
onset=np.zeros(100,np.float32);onset[:2]=1
out=apply_string_physical_residuals(dyn,vib,exp,leg,trans,tight,attack,bow,pb,phys,onset=onset)
assert float(out[3].mean())>.70
assert float(out[4].mean())<.40
assert float(out[7][:2].mean())>.80 and float(out[7][10:].mean())<.1
print("SONICRAFT v4.2 physical planner/runtime smoke OK")
# Partial authored physical state must not imply missing Position/Open String.
partial=physical_curves([{'project_sample':0,'type':4,'note':116,'velocity':.8}],0,48000,100,100)
v=np.full(100,.55,np.float32)
partial_out=apply_string_physical_residuals(dyn,v,exp,leg,trans,tight,attack,bow,pb,partial,onset=np.zeros(100,np.float32))
assert float(partial_out[1].mean())>.50
