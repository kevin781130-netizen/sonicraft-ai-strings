import numpy as np
from string_transition_runtime_v46 import apply_continuous_transition_paths_v46,multi_note_gesture_active_v46
sr=48000.;fps=100;N=100
# Two independent v4.5 windows, one for each note.
events=[
 {"project_sample":0,"type":4,"note":122,"velocity":.8},
 {"project_sample":0,"type":1,"note":72,"velocity":.8},
 {"project_sample":23990,"type":2,"note":72,"velocity":0.},
 {"project_sample":24000,"type":4,"note":122,"velocity":0.},
 {"project_sample":24000,"type":4,"note":122,"velocity":.8},
 {"project_sample":24000,"type":1,"note":79,"velocity":.8},
 {"project_sample":47990,"type":2,"note":79,"velocity":0.},
 {"project_sample":48000,"type":4,"note":122,"velocity":0.},
]
assert not multi_note_gesture_active_v46(events,0,48000)
pitch=np.r_[np.full(50,72.,np.float32),np.full(50,79.,np.float32)]
gate=np.ones(N,np.float32);onset=np.zeros(N,np.float32);onset[:2]=1;onset[50:52]=1
prog=np.r_[np.linspace(0,1,50,endpoint=False,dtype=np.float32),np.linspace(0,1,50,endpoint=False,dtype=np.float32)]
leg=np.ones(N,np.float32);trans=np.full(N,.3,np.float32);vib=np.full(N,.5,np.float32);vo=np.zeros(N,np.float32);pb=np.full(N,.6,np.float32)
notes=[{"note":72,"on":0,"off":50,"on_sample":0,"off_sample":23990},{"note":79,"on":50,"off":100,"on_sample":24000,"off_sample":47990}]
out=apply_continuous_transition_paths_v46(notes,pitch,gate,onset,prog,leg,trans,vib,vo,pb,events,0,48000,sr,fps,np.full(N,.8,np.float32))
assert out[-1]==0
assert np.array_equal(out[0],pitch)
assert np.array_equal(out[8],pb)
assert out[2][50]==1
print("SONICRAFT v4.6 legacy v4.5 transition gate regression OK")
