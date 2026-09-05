"""NumPy-only v2.8 virtual scoring stage: Master + 16 stereo feeds (34 channels)."""
from __future__ import annotations
import json,math,os
from pathlib import Path
import numpy as np
MIC_NAMES=('spot_l','spot_c','spot_r','tree_l','tree_c','tree_r','wide_l','wide_r','room_l','room_r','rear','mid_l','mid_r','far_l','far_r','gallery')
CFG=((0.,.02,0.,-.45),(0.,.01,0.,0.),(0.,.02,0.,.45),(3.2,.08,.08,-.55),(3.8,.07,.09,0.),(3.2,.08,.08,.55),(7.4,.13,.12,-.78),(7.4,.13,.12,.78),(12.5,.22,.22,-.62),(13.1,.22,.22,.62),(18.,.28,.27,0.),(8.8,.16,.15,-.40),(8.8,.16,.15,.40),(21.,.34,.31,-.64),(21.,.34,.31,.64),(27.,.40,.36,0.))
PRESETS=((1,.7,.7,1,1,1,.02,.02,0,0,0,.08,.08,0,0,0),(.42,.32,.32,.58,.66,.58,.2,.2,.12,.12,.04,.24,.24,.05,.05,.02),(.3,.22,.22,.48,.55,.48,.52,.52,.24,.24,.08,.35,.35,.12,.12,.05),(.18,.14,.14,.3,.36,.3,.38,.38,.58,.58,.24,.26,.26,.34,.34,.18))
def _delay(x,n):
    if n<=0:return x.copy()
    y=np.zeros_like(x)
    if n<len(x):y[n:]=x[:-n]
    return y
def _air(x,a):
    a=float(np.clip(a,0,1));y=x.copy()
    if len(x)>1:y[1:]=(1-a)*x[1:]+a*.5*(x[1:]+x[:-1])
    return y
def _profile():
    raw=os.getenv('SONICRAFT_ROOM_PROFILE','').strip();p=Path(raw) if raw else Path(__file__).resolve().parent.parent/'Room'/'active_room_profile.json'
    try:
        d=json.loads(p.read_text(encoding='utf-8'));return d if int(d.get('schema',0))==1 else None
    except Exception:return None
def _fir(x,h):
    h=np.asarray(h or [1.],np.float32)[:128];return np.convolve(x,h,mode='full')[:len(x)].astype(np.float32)
def stage_bundle_np(mono,sr,room=.18,perspective=1):
    x=np.asarray(mono,np.float32);prof=_profile();pairs=[]
    for i,(ms,air,early,pan) in enumerate(CFG):
        d=int(round(ms*sr/1000));y=_air(_delay(x,d),air+float(room)*.18)
        if early:y+=_delay(x,d+int(round((4+1.7*(i%3))*sr/1000)))*(early*(.45+.55*float(room)))
        ent=(prof.get('feeds',{}).get(MIC_NAMES[i],{}) if prof else {})
        if ent:
            y=_delay(y,int(round(float(ent.get('delay_samples',0))*sr/max(1,int(prof.get('sample_rate',sr))))))*float(ent.get('gain',1));pan=float(ent.get('pan',pan))
        if ent and (ent.get('left_fir') or ent.get('right_fir')):l=_fir(y,ent.get('left_fir'));r=_fir(y,ent.get('right_fir'))
        else:l=y*math.sqrt(.5*(1-pan));r=y*math.sqrt(.5*(1+pan))
        pairs.append(np.stack([l,r],-1))
    feeds=np.concatenate(pairs,-1);w=PRESETS[max(0,min(3,int(perspective)))];master=np.zeros((len(x),2),np.float32);den=0.
    for i,wi in enumerate(w):master[:,0]+=feeds[:,2*i]*wi;master[:,1]+=feeds[:,2*i+1]*wi;den+=wi
    if den>0:master/=math.sqrt(den)
    return np.concatenate([master,feeds],-1).astype(np.float32)
