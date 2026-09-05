import numpy as np
from string_gesture_runtime_v45 import gesture_windows_v45,smooth_voice_controls_v45,smooth_physical_curves_v45
from string_physical_runtime_v42 import physical_curves
sr=48000;fps=100;N=100
base=[.2,.2,.9,.86,.5,1,1,.18,.5,0,.5,.5,.3,0]
hi=base.copy();hi[0]=.8;hi[1]=.7;hi[8]=.6;hi[10]=.3;hi[12]=.7
events=[
 {'project_sample':0,'type':4,'note':122,'velocity':1.0,'controls':base},
 {'project_sample':0,'type':4,'note':0,'velocity':0.,'controls':base},
 {'project_sample':24000,'type':4,'note':0,'velocity':0.,'controls':hi},
 {'project_sample':0,'type':4,'note':116,'velocity':.2,'controls':base},
 {'project_sample':24000,'type':4,'note':116,'velocity':.8,'controls':hi},
 {'project_sample':48000,'type':4,'note':122,'velocity':0.0,'controls':hi},]
assert gesture_windows_v45(events,0,48000)==[(0,48000,1.0)]
arr=[np.full(N,v,np.float32) for v in [.2,.2,.9,1,.5,.5,.5,.3,0]]
out=smooth_voice_controls_v45(events,0,48000,sr,fps,arr)
assert .45<float(out[0][25])<.60 and .65<float(out[0][45])<.80
phys=physical_curves(events,0,sr,fps,N);phys=smooth_physical_curves_v45(phys,events,0,48000,sr,fps)
assert .35<float(phys[116][25])<.55 and .65<float(phys[116][45])<.85
legacy=[{'project_sample':0,'type':4,'note':0,'velocity':0.,'controls':base}]
assert smooth_voice_controls_v45(legacy,0,48000,sr,fps,arr)[0] is not None
print('SONICRAFT v4.5 gesture runtime interpolation smoke OK')
