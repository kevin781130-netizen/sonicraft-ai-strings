from __future__ import annotations
import numpy as np
from polyphony import allocate_polyphonic_event_lanes
from control_builder_np import build_part_controls_np

class Req:
    sample_rate=48000;start_sample=0;end_sample=24000;tempo_bpm=80.
    # polyphony on + All retake, nonce 77, amount max, Authority lock.
    flags=(1<<7)|(7<<8)|(77<<11)|(15<<21)|(1<<26)
req=Req()
base=[.62,.5,.9,.86,.5,1,1,.18,.5,0,.5,.5,.38,0]
a=base.copy();a[0]=.42;a[10]=.35;a[12]=.70
b=base.copy();b[0]=.86;b[10]=.65;b[12]=.22
events=[
 {'project_sample':0,'type':4,'part':0,'voice_lane':0,'note':0,'articulation':(1<<4)|7,'velocity':0.,'tempo_bpm':80.,'controls':a},
 {'project_sample':0,'type':1,'part':0,'voice_lane':0,'note':72,'articulation':(1<<4)|7,'velocity':.8,'tempo_bpm':80.,'controls':a},
 {'project_sample':24000,'type':2,'part':0,'voice_lane':0,'note':72,'articulation':(1<<4)|7,'velocity':0.,'tempo_bpm':80.,'controls':a},
 {'project_sample':0,'type':4,'part':0,'voice_lane':4,'note':0,'articulation':(4<<4)|0,'velocity':0.,'tempo_bpm':80.,'controls':b},
 {'project_sample':0,'type':1,'part':0,'voice_lane':4,'note':76,'articulation':(4<<4)|0,'velocity':.8,'tempo_bpm':80.,'controls':b},
 {'project_sample':24000,'type':2,'part':0,'voice_lane':4,'note':76,'articulation':(4<<4)|0,'velocity':0.,'tempo_bpm':80.,'controls':b},
]
lanes=allocate_polyphonic_event_lanes(events,0,16)
assert len(lanes)==2
c0=build_part_controls_np(req,lanes[0],0,'v41')
c1=build_part_controls_np(req,lanes[1],0,'v41')
art0=int(c0['articulation_curve'][0,0]);art1=int(c1['articulation_curve'][0,0])
assert {art0,art1}=={0,7},(art0,art1)
# Independent lane-authored dynamics survive; Retake curves must not collapse to identical data.
d0=c0['raw'][0,:,4];d1=c1['raw'][0,:,4]
assert abs(float(d0.mean())-float(d1.mean()))>.10
assert not np.allclose(c0['raw'][0,:,11],c1['raw'][0,:,11])
print("SONICRAFT v4.1 explicit String Voice HQ isolation smoke OK",art0,art1,round(float(d0.mean()),3),round(float(d1.mean()),3))
