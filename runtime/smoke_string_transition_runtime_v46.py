import numpy as np
from string_transition_runtime_v46 import apply_continuous_transition_paths_v46,multi_note_gesture_active_v46

sr=48000.;fps=100;start=0;end=48000
# One continuous CC38 window over C5 -> G5. CC39 holds +10 cents across the phrase.
events=[
 {"project_sample":0,"type":4,"note":122,"velocity":.8},
 {"project_sample":0,"type":4,"note":0,"velocity":0.,"controls":[.62,.5,.9,.86,.5,1,1,.18,.60,0,.35,.5,.38,0]},
 {"project_sample":0,"type":1,"note":72,"velocity":.8},
 {"project_sample":23800,"type":4,"note":0,"velocity":0.,"controls":[.64,.55,.9,.86,.5,1,1,.18,.60,0,.28,.5,.34,0]},
 {"project_sample":24000,"type":2,"note":72,"velocity":0.},
 {"project_sample":24000,"type":1,"note":79,"velocity":.8},
 {"project_sample":24200,"type":4,"note":0,"velocity":0.,"controls":[.66,.56,.9,.86,.5,1,1,.18,.60,0,.28,.5,.34,0]},
 {"project_sample":47900,"type":2,"note":79,"velocity":0.},
 {"project_sample":48000,"type":4,"note":122,"velocity":0.},
]
assert multi_note_gesture_active_v46(events,start,end)
N=100
pitch=np.r_[np.full(50,72.,np.float32),np.full(50,79.,np.float32)]
gate=np.ones(N,np.float32);onset=np.zeros(N,np.float32);onset[:2]=1;onset[50:52]=1
prog=np.r_[np.linspace(0,1,50,endpoint=False,dtype=np.float32),np.linspace(0,1,50,endpoint=False,dtype=np.float32)]
leg=np.ones(N,np.float32);trans=np.full(N,.3,np.float32);vib=np.full(N,.5,np.float32);vib_on=np.zeros(N,np.float32)
pb=np.full(N,.60,np.float32)
porta=np.full(N,.75,np.float32)
notes=[
 {"note":72,"on":0,"off":50,"on_sample":0,"off_sample":24000},
 {"note":79,"on":50,"off":100,"on_sample":24000,"off_sample":47900},
]
out=apply_continuous_transition_paths_v46(notes,pitch,gate,onset,prog,leg,trans,vib,vib_on,pb,events,start,end,sr,fps,porta)
p,_,o,npgr,l,tr,v,vo,pbend,tms,links=out
assert links==1
assert o[50]==0 and o[51]==0
assert np.max(tms)>50
assert p[49] > 72.5 and p[50] < 78.8, (p[47:53],tms[47:53])
assert np.allclose(pbend,.5)
# +10 cents authored CC39 is now applied directly to float MIDI pitch in the v4.6 phrase.
assert p[10]>72.09 and p[90]>79.09
assert npgr[50]>=.12
print("SONICRAFT v4.6 transition runtime smoke OK",links,round(float(np.max(tms)),2),[round(float(x),3) for x in p[47:53]])
