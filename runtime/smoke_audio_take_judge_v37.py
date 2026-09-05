from __future__ import annotations
import numpy as np
from audio_take_judge_v37 import judge_take,rank_takes
sr=48000;n=sr
t=np.arange(n)/sr
events=[
 {'project_sample':0,'type':1,'controls':[.35]+[0]*13},
 {'project_sample':sr//2,'type':1,'controls':[.8]+[0]*13},
]
# A: follows authored dynamics, healthy headroom.
a=np.concatenate([.10*np.sin(2*np.pi*220*t[:n//2]),.28*np.sin(2*np.pi*220*t[n//2:])]).astype(np.float32)
# B: flat dynamics.
b=.16*np.sin(2*np.pi*220*t).astype(np.float32)
# C: deliberate clipping/spikes.
c=a.copy();c[::300]=1.0
# D: abrupt high-frequency chatter away from onsets.
d=a.copy();d += (.05*np.sign(np.sin(2*np.pi*7000*t))).astype(np.float32)
winner,s=rank_takes([a,b,c,d],sr,events,0,n)
assert winner==0,(winner,[x.overall for x in s])
assert s[0].dynamics>s[1].dynamics
assert s[0].safety>s[2].safety
assert s[0].transition>s[3].transition
# Human review still dominates.
winner2,_=rank_takes([a,b,c,d],sr,events,0,n,favorite_mask=1<<1)
assert winner2==1
winner3,_=rank_takes([a,b,c,d],sr,events,0,n,favorite_mask=1<<1,reject_mask=1<<1)
assert winner3!=1
print("SONICRAFT v3.7 audio take judge smoke OK",winner,[round(x.overall,4) for x in s])
