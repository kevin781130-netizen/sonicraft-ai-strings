import numpy as np
from string_phrase_runtime_v47 import phrase_windows_v47,apply_phrase_longline_v47
N=120;sr=48000.;fps=100
# v4.6-like phrase without sentinel must remain untouched.
legacy=[{"project_sample":0,"type":4,"note":122,"velocity":.8},{"project_sample":48000,"type":4,"note":122,"velocity":0.}]
assert phrase_windows_v47(legacy,0,48000)==[]
base=np.full(N,.6,np.float32);vib=np.full(N,.5,np.float32);exp=np.full(N,.9,np.float32)
attack=np.full(N,.4,np.float32);tight=np.full(N,.5,np.float32);bow=np.full(N,.1,np.float32);vo=np.full(N,.3,np.float32)
out=apply_phrase_longline_v47(base,vib,exp,attack,tight,bow,vo,legacy,0,48000,sr,fps)
assert out[-1]==0 and np.array_equal(out[0],base)

# v4.7 sentinel + normal gesture amount activates phrase shaping.
events=[
 {"project_sample":0,"type":4,"note":122,"velocity":1/127},
 {"project_sample":1,"type":4,"note":122,"velocity":.8},
 {"project_sample":48000,"type":4,"note":122,"velocity":0.},
]
out=apply_phrase_longline_v47(base,vib,exp,attack,tight,bow,vo,events,0,48000,sr,fps)
dyn,v,ex,at,ti,bo,von,depth,rate,mom,count=out
assert count==1
assert float(rate.max())>5.5 and float(rate.min())>=0
assert float(depth.max())>15
assert float(mom.max())>.95
assert not np.array_equal(dyn,base)
print("SONICRAFT v4.7 phrase runtime sentinel/long-line smoke OK",round(float(rate.max()),3),round(float(depth.max()),3))
