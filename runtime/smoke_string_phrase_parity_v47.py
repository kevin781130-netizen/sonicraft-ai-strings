from types import SimpleNamespace
import numpy as np,torch
from model_backend import TorchFlowBackend
from control_builder_np import build_part_controls_np,RAW_NAMES

flags=(2)|(5<<2)|(1<<5)|(1<<6)|(1<<7)|(7<<8)|(77<<11)|(12<<21)|(1<<26)|(1<<27)|(9<<28)
req=SimpleNamespace(sample_rate=48000,start_sample=0,end_sample=48000,tempo_bpm=90.0,flags=flags)
c0=[.60,.42,.9,.86,.5,1,1,.18,.50,1/11,.34,.5,.34,0]
c1=[.66,.56,.9,.86,.5,1,1,.18,.50,1/11,.28,.5,.30,0]
events=[
 {'project_sample':0,'part':0,'voice_lane':0,'type':4,'note':122,'articulation':1,'velocity':1/127,'tempo_bpm':90.,'controls':c0},
 {'project_sample':1,'part':0,'voice_lane':0,'type':4,'note':122,'articulation':1,'velocity':.85,'tempo_bpm':90.,'controls':c0},
 {'project_sample':0,'part':0,'voice_lane':0,'type':1,'note':69,'articulation':1,'velocity':.8,'tempo_bpm':90.,'controls':c0},
 {'project_sample':22000,'part':0,'voice_lane':0,'type':4,'note':0,'articulation':1,'velocity':0.,'tempo_bpm':90.,'controls':c1},
 {'project_sample':24000,'part':0,'voice_lane':0,'type':2,'note':69,'articulation':1,'velocity':0.,'tempo_bpm':90.,'controls':c1},
 {'project_sample':24000,'part':0,'voice_lane':0,'type':1,'note':76,'articulation':1,'velocity':.82,'tempo_bpm':90.,'controls':c1},
 {'project_sample':47900,'part':0,'voice_lane':0,'type':2,'note':76,'articulation':1,'velocity':0.,'tempo_bpm':90.,'controls':c1},
 {'project_sample':48000,'part':0,'voice_lane':0,'type':4,'note':122,'articulation':1,'velocity':0.,'tempo_bpm':90.,'controls':c1},
]
b=TorchFlowBackend.__new__(TorchFlowBackend);b.torch=torch;b.device='cpu';b.fingerprint=lambda:'phrase-v47-parity'
tc=b._build_part_controls(req,events,0)
nc=build_part_controls_np(req,events,0,fingerprint='phrase-v47-parity')
for i,name in enumerate(RAW_NAMES):
    tv=tc[name].detach().cpu().numpy().astype(np.float32)
    nv=nc['raw'][...,i].astype(np.float32)
    if not np.allclose(tv,nv,rtol=0,atol=2e-6):
        raise AssertionError((name,float(np.max(np.abs(tv-nv)))))
vr=nc['raw'][0,:,RAW_NAMES.index('vibrato_rate_hz')]
vd=nc['raw'][0,:,RAW_NAMES.index('vibrato_depth_cents')]
assert float(vr.max())>5.5 and float(vd.max())>15
print("SONICRAFT v4.7 phrase Torch/NumPy parity smoke OK",round(float(vr.max()),3),round(float(vd.max()),3))
