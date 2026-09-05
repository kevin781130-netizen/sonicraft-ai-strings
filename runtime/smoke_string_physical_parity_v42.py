from types import SimpleNamespace
import numpy as np, torch
from model_backend import TorchFlowBackend
from control_builder_np import build_part_controls_np,RAW_NAMES

flags=(2)|(5<<2)|(1<<5)|(1<<6)|(1<<7)|(7<<8)|(77<<11)|(12<<21)|(1<<26)|(1<<27)|(9<<28)
req=SimpleNamespace(sample_rate=48000,start_sample=0,end_sample=48000,tempo_bpm=72.0,flags=flags)
c=[.64,.52,.9,.86,.5,1,1,.18,.5,1/11,.5,.5,.38,0]
events=[
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':112,'articulation':1,'velocity':.67,'tempo_bpm':72.,'controls':c},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':113,'articulation':1,'velocity':.57,'tempo_bpm':72.,'controls':c},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':114,'articulation':1,'velocity':1.,'tempo_bpm':72.,'controls':c},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':115,'articulation':1,'velocity':1.,'tempo_bpm':72.,'controls':c},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':116,'articulation':1,'velocity':.78,'tempo_bpm':72.,'controls':c},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':117,'articulation':1,'velocity':.72,'tempo_bpm':72.,'controls':c},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':118,'articulation':1,'velocity':.66,'tempo_bpm':72.,'controls':c},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':119,'articulation':1,'velocity':.33,'tempo_bpm':72.,'controls':c},
 {'project_sample':0,'part':0,'voice_lane':0,'type':1,'note':72,'articulation':1,'velocity':.82,'tempo_bpm':72.,'controls':c},
 {'project_sample':47000,'part':0,'voice_lane':0,'type':2,'note':72,'articulation':1,'velocity':0.,'tempo_bpm':72.,'controls':c},
]
b=TorchFlowBackend.__new__(TorchFlowBackend);b.torch=torch;b.device='cpu';b.fingerprint=lambda:'physical-parity-v42'
tc=b._build_part_controls(req,events,0)
nc=build_part_controls_np(req,events,0,fingerprint='physical-parity-v42')
for i,name in enumerate(RAW_NAMES):
    tv=tc[name].detach().cpu().numpy().astype(np.float32)
    nv=nc['raw'][...,i].astype(np.float32)
    if not np.allclose(tv,nv,rtol=0,atol=2e-6):
        raise AssertionError((name,float(np.max(np.abs(tv-nv)))))
assert np.allclose(tc['frontier_context'].detach().cpu().numpy(),nc['frontier_context'],rtol=0,atol=2e-6)
print("SONICRAFT v4.2 physical Torch/NumPy parity smoke OK")
