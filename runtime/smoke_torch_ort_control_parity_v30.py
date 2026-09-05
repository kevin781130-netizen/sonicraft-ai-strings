from types import SimpleNamespace
import numpy as np, torch
from model_backend import TorchFlowBackend
from control_builder_np import build_part_controls_np, RAW_NAMES

# Flags: Auto assist, Ballade, smart dynamics/articulation, polyphony, ALL retake, nonce 77,
# amount 12/15, authority unlocked, phrase director, looseness 9/15.
flags=(2) | (5<<2) | (1<<5) | (1<<6) | (1<<7) | (7<<8) | (77<<11) | (12<<21) | (0<<26) | (1<<27) | (9<<28)
req=SimpleNamespace(sample_rate=48000,start_sample=0,end_sample=48000,tempo_bpm=68.0,flags=flags)
def ctrl(d=.62,v=.5,exp=.9,leg=1.,pb=.5,art=0,trans=.5,tight=.5,attack=.38,speed=0):
    return [d,v,exp,.86,.5,1,leg,.18,pb,art/11,trans,tight,attack,speed]
events=[
 {'project_sample':0,'part':0,'type':1,'note':72,'velocity':.82,'controls':ctrl(art=1)},
 {'project_sample':18000,'part':1,'type':1,'note':67,'velocity':.78,'controls':ctrl(art=0)},
 {'project_sample':22000,'part':1,'type':2,'note':67,'velocity':0.,'controls':ctrl()},
 {'project_sample':24000,'part':0,'type':2,'note':72,'velocity':0.,'controls':ctrl()},
 {'project_sample':24500,'part':0,'type':1,'note':76,'velocity':.88,'controls':ctrl(d=.7,v=.7,art=0,trans=.65)},
 {'project_sample':47000,'part':0,'type':2,'note':76,'velocity':0.,'controls':ctrl()},
]
b=TorchFlowBackend.__new__(TorchFlowBackend); b.torch=torch; b.device='cpu'; b.fingerprint=lambda:'parity-v30'
t=b._build_part_controls(req,events,0)
n=build_part_controls_np(req,events,0,fingerprint='parity-v30')
for i,name in enumerate(RAW_NAMES):
    tv=t[name].detach().cpu().numpy().astype(np.float32)
    nv=n['raw'][...,i].astype(np.float32)
    if not np.allclose(tv,nv,rtol=0,atol=2e-6):
        raise AssertionError((name,float(np.max(np.abs(tv-nv)))))
assert np.allclose(t['frontier_context'].detach().cpu().numpy(),n['frontier_context'],rtol=0,atol=2e-6)
print('SONICRAFT v3.0 Torch/NumPy performance-control parity smoke OK')
