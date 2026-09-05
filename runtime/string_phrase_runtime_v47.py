"""SONICRAFT v4.7 opt-in phrase-longline runtime.

Activation is backwards-compatible and uses no new CC:
- v4.7 emits CC38 value 1/127 as a sentinel at phrase start,
- followed immediately by the normal non-zero Gesture Amount,
- phrase ends at the existing CC38 zero.

v4.6 files never emit a bowed Gesture Amount this small, so they remain unchanged.
"""
from __future__ import annotations
import numpy as np

SENTINEL_MAX=.02

def phrase_windows_v47(events,start_sample,end_sample):
    ev=sorted(events,key=lambda e:(int(e.get("project_sample",0)),0 if int(e.get("type",0))==4 else 1))
    out=[];armed=None;active=None
    for e in ev:
        if int(e.get("type",0))!=4 or int(e.get("note",-1))!=122:continue
        ps=int(e.get("project_sample",0));v=max(0.,min(1.,float(e.get("velocity",0.))))
        if 0<v<=SENTINEL_MAX:
            armed=ps
        elif v>0 and armed is not None and active is None and ps-armed<=256:
            active=armed;armed=None
        elif v<=0 and active is not None:
            out.append((max(int(start_sample),active),min(int(end_sample),ps)));active=None
    if active is not None:out.append((max(int(start_sample),active),int(end_sample)))
    return [(a,b) for a,b in out if b>a]

def _idx(ps,start,sr,fps,n):
    return int(max(0,min(n-1,round((int(ps)-int(start))/float(sr)*fps))))

def _arch(u):
    u=np.asarray(u,np.float32)
    apex=.62
    left=np.clip(u/apex,0,1);right=np.clip((u-apex)/(1-apex),0,1)
    sl=left*left*(3-2*left);sr=right*right*(3-2*right)
    return np.where(u<=apex,.90+.18*sl,1.08-.20*sr).astype(np.float32)

def apply_phrase_longline_v47(dyn,vib,exp,attack,tight,bow,vib_on,events,start_sample,end_sample,sr,fps):
    windows=phrase_windows_v47(events,start_sample,end_sample)
    n=len(dyn)
    depth_cents=np.zeros(n,np.float32);rate_hz=np.zeros(n,np.float32);momentum=np.zeros(n,np.float32)
    if not windows:
        return dyn,vib,exp,attack,tight,bow,vib_on,depth_cents,rate_hz,momentum,0

    dyn=np.asarray(dyn,np.float32).copy();vib=np.asarray(vib,np.float32).copy();exp=np.asarray(exp,np.float32).copy()
    attack=np.asarray(attack,np.float32).copy();tight=np.asarray(tight,np.float32).copy()
    bow=np.asarray(bow,np.float32).copy();vib_on=np.asarray(vib_on,np.float32).copy()
    for a,b in windows:
        ia=_idx(a,start_sample,sr,fps,n);ib=_idx(b,start_sample,sr,fps,n)
        if ib<=ia:continue
        L=ib-ia+1;u=np.linspace(0,1,L,dtype=np.float32);arc=_arch(u)
        mom=np.clip((arc-.90)/.18,0,1)
        # Long-line dynamic momentum is intentionally shallow: authored CC remains authoritative.
        dyn[ia:ib+1]=np.clip(dyn[ia:ib+1]*(.965+.06*mom),0,1)
        exp[ia:ib+1]=np.clip(exp[ia:ib+1]+(.018*mom),0,1)
        # Vibrato evolves over the phrase instead of restarting its rate/depth target per note.
        vib[ia:ib+1]=np.clip(vib[ia:ib+1]*(.94+.12*mom),0,1)
        depth_cents[ia:ib+1]=8.0+26.0*vib[ia:ib+1]
        rate_hz[ia:ib+1]=4.65+1.05*mom
        # Bow energy: slightly round the middle of the line and release the tail.
        attack[ia:ib+1]=np.clip(attack[ia:ib+1]-(.025*mom),0,1)
        tight[ia:ib+1]=np.clip(tight[ia:ib+1]-(.018*mom),0,1)
        # Avoid phrase-internal random bow-change probability except authored transition/onset anchors.
        interior=np.ones(L,np.float32);interior[:2]=1;interior[-2:]=1
        if L>6:interior[2:-2]=.72
        bow[ia:ib+1]=np.clip(bow[ia:ib+1]*interior,0,1)
        # Continuous phrases should not repeatedly delay vibrato bloom at every linked note.
        vib_on[ia:ib+1]=np.minimum(vib_on[ia:ib+1],.10+.06*(1-mom))
        momentum[ia:ib+1]=mom
    return dyn,vib,exp,attack,tight,bow,vib_on,depth_cents,rate_hz,momentum,len(windows)
