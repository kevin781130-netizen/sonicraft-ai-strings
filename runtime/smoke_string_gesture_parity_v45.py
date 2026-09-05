from types import SimpleNamespace
import numpy as np, torch
from model_backend import TorchFlowBackend
from control_builder_np import build_part_controls_np,RAW_NAMES
flags=(2)|(5<<2)|(1<<5)|(1<<6)|(1<<7)|(7<<8)|(77<<11)|(12<<21)|(1<<26)|(1<<27)|(9<<28)
req=SimpleNamespace(sample_rate=48000,start_sample=0,end_sample=48000,tempo_bpm=72.0,flags=flags)
a=[.45,.22,.9,.86,.5,1,1,.18,.5,1/11,.55,.5,.38,0]
b=a.copy();b[0]=.82;b[1]=.70;b[8]=.58;b[10]=.30;b[12]=.68
m=a.copy();m[0]=.64;m[1]=.48;m[8]=.54;m[10]=.42;m[12]=.54
events=[
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':122,'articulation':1,'velocity':1.,'tempo_bpm':72.,'controls':a},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':0,'articulation':1,'velocity':0.,'tempo_bpm':72.,'controls':a},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':116,'articulation':1,'velocity':.35,'tempo_bpm':72.,'controls':a},
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':117,'articulation':1,'velocity':.42,'tempo_bpm':72.,'controls':a},
 {'project_sample':1000,'part':0,'voice_lane':0,'type':1,'note':72,'articulation':1,'velocity':.82,'tempo_bpm':72.,'controls':a},
 {'project_sample':18000,'part':0,'voice_lane':0,'type':4,'note':0,'articulation':1,'velocity':0.,'tempo_bpm':72.,'controls':m},
 {'project_sample':18000,'part':0,'voice_lane':0,'type':4,'note':116,'articulation':1,'velocity':.62,'tempo_bpm':72.,'controls':m},
 {'project_sample':18000,'part':0,'voice_lane':0,'type':4,'note':117,'articulation':1,'velocity':.58,'tempo_bpm':72.,'controls':m},
 {'project_sample':36000,'part':0,'voice_lane':0,'type':4,'note':0,'articulation':1,'velocity':0.,'tempo_bpm':72.,'controls':b},
 {'project_sample':36000,'part':0,'voice_lane':0,'type':4,'note':116,'articulation':1,'velocity':.78,'tempo_bpm':72.,'controls':b},
 {'project_sample':36000,'part':0,'voice_lane':0,'type':4,'note':117,'articulation':1,'velocity':.68,'tempo_bpm':72.,'controls':b},
 {'project_sample':47000,'part':0,'voice_lane':0,'type':2,'note':72,'articulation':1,'velocity':0.,'tempo_bpm':72.,'controls':b},
 {'project_sample':48000,'part':0,'voice_lane':0,'type':4,'note':122,'articulation':1,'velocity':0.,'tempo_bpm':72.,'controls':b},
]
tb=TorchFlowBackend.__new__(TorchFlowBackend);tb.torch=torch;tb.device='cpu';tb.fingerprint=lambda:'gesture-parity-v45'
tc=tb._build_part_controls(req,events,0);nc=build_part_controls_np(req,events,0,fingerprint='gesture-parity-v45')
for i,name in enumerate(RAW_NAMES):
    tv=tc[name].detach().cpu().numpy().astype(np.float32);nv=nc['raw'][...,i].astype(np.float32)
    if not np.allclose(tv,nv,rtol=0,atol=2e-6):raise AssertionError((name,float(np.max(np.abs(tv-nv)))))
assert np.allclose(tc['frontier_context'].detach().cpu().numpy(),nc['frontier_context'],rtol=0,atol=2e-6)
print('SONICRAFT v4.5 gesture Torch/NumPy parity smoke OK')
