from types import SimpleNamespace
import numpy as np,torch
from model_backend import TorchFlowBackend
from control_builder_np import build_part_controls_np,RAW_NAMES

flags=(2)|(5<<2)|(1<<5)|(1<<6)|(1<<7)|(7<<8)|(77<<11)|(12<<21)|(1<<26)|(1<<27)|(9<<28)
req=SimpleNamespace(sample_rate=48000,start_sample=0,end_sample=48000,tempo_bpm=88.0,flags=flags)
c0=[.62,.52,.9,.86,.5,1,1,.18,.57,1/11,.28,.5,.34,0]
c1=[.66,.55,.9,.86,.5,1,1,.18,.61,2/11,.24,.5,.30,0]
events=[
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':122,'articulation':1,'velocity':.85,'tempo_bpm':88.,'controls':c0},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':118,'articulation':1,'velocity':.72,'tempo_bpm':88.,'controls':c0},
 {'project_sample':0,'part':0,'voice_lane':0,'type':1,'note':69,'articulation':1,'velocity':.8,'tempo_bpm':88.,'controls':c0},
 {'project_sample':22000,'part':0,'voice_lane':0,'type':4,'note':0,'articulation':2,'velocity':0.,'tempo_bpm':88.,'controls':c1},
 {'project_sample':24000,'part':0,'voice_lane':0,'type':2,'note':69,'articulation':1,'velocity':0.,'tempo_bpm':88.,'controls':c1},
 {'project_sample':24000,'part':0,'voice_lane':0,'type':1,'note':76,'articulation':2,'velocity':.82,'tempo_bpm':88.,'controls':c1},
 {'project_sample':47900,'part':0,'voice_lane':0,'type':2,'note':76,'articulation':2,'velocity':0.,'tempo_bpm':88.,'controls':c1},
 {'project_sample':48000,'part':0,'voice_lane':0,'type':4,'note':122,'articulation':2,'velocity':0.,'tempo_bpm':88.,'controls':c1},
]
b=TorchFlowBackend.__new__(TorchFlowBackend);b.torch=torch;b.device='cpu';b.fingerprint=lambda:'transition-v46-parity'
tc=b._build_part_controls(req,events,0)
nc=build_part_controls_np(req,events,0,fingerprint='transition-v46-parity')
for i,name in enumerate(RAW_NAMES):
    tv=tc[name].detach().cpu().numpy().astype(np.float32)
    nv=nc['raw'][...,i].astype(np.float32)
    if not np.allclose(tv,nv,rtol=0,atol=2e-6):
        raise AssertionError((name,float(np.max(np.abs(tv-nv)))))
pitch=nc['raw'][0,:,RAW_NAMES.index('pitch')]
tms=nc['raw'][0,:,RAW_NAMES.index('transition_target_ms')]
onset=nc['raw'][0,:,RAW_NAMES.index('onset')]
assert np.max(tms)>0
assert onset[50]==0
assert np.any((pitch>69.5)&(pitch<75.5))
print("SONICRAFT v4.6 transition Torch/NumPy parity smoke OK",round(float(np.max(tms)),2))
