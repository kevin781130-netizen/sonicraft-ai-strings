"""SONICRAFT clean-room virtual scoring stage v2.2.

No proprietary room measurements are used. The built-in stage is a deterministic geometric
model. A user-owned/SONICRAFT-owned calibration profile can optionally replace each virtual
feed's pan/FIR response. Sixteen stereo virtual auxiliary feeds plus a stereo master are supported in v2.8.
"""
from __future__ import annotations
import json, math, os
from functools import lru_cache
from pathlib import Path

MIC_NAMES=('spot_l','spot_c','spot_r','tree_l','tree_c','tree_r','wide_l','wide_r','room_l','room_r','rear','mid_l','mid_r','far_l','far_r','gallery')
_DEFAULT_CFG=((0.0,.02,.00,-.45),(0.0,.01,.00,0.0),(0.0,.02,.00,.45),
              (3.2,.08,.08,-.55),(3.8,.07,.09,0.0),(3.2,.08,.08,.55),
              (7.4,.13,.12,-.78),(7.4,.13,.12,.78),(12.5,.22,.22,-.62),(13.1,.22,.22,.62),(18.0,.28,.27,0.0),
              (8.8,.16,.15,-.40),(8.8,.16,.15,.40),(21.0,.34,.31,-.64),(21.0,.34,.31,.64),(27.0,.40,.36,0.0))
_PRESETS=(
    (1.00,.70,.70,.10,.10,.10,.02,.02,.00,.00,.00,.08,.08,.00,.00,.00),
    (.42,.32,.32,.58,.66,.58,.20,.20,.12,.12,.04,.24,.24,.05,.05,.02),
    (.30,.22,.22,.48,.55,.48,.52,.52,.24,.24,.08,.35,.35,.12,.12,.05),
    (.18,.14,.14,.30,.36,.30,.38,.38,.58,.58,.24,.26,.26,.34,.34,.18),
)

def _delay(x,n,torch):
    if n<=0:return x
    if n>=x.numel():return torch.zeros_like(x)
    y=torch.zeros_like(x);y[n:]=x[:-n];return y

def _air(x,amount,torch):
    a=float(max(0.0,min(1.0,amount)))
    if x.numel()<2:return x
    y=x.clone();y[1:]=(1-a)*x[1:]+a*.5*(x[1:]+x[:-1]);return y

def _profile_path():
    raw=os.getenv('SONICRAFT_ROOM_PROFILE','').strip()
    if raw:return Path(raw)
    here=Path(__file__).resolve().parent.parent
    candidate=here/'Room'/'active_room_profile.json'
    return candidate if candidate.is_file() else None

@lru_cache(maxsize=4)
def _load_profile_cached(path_text,mtime_ns):
    if not path_text:return None
    try:
        d=json.loads(Path(path_text).read_text(encoding='utf-8'))
        if int(d.get('schema',0))!=1:return None
        feeds=d.get('feeds') or {}
        if not all(name in feeds for name in MIC_NAMES):return None
        return d
    except Exception:return None

def active_room_profile():
    p=_profile_path()
    if not p:return None
    try:return _load_profile_cached(str(p),p.stat().st_mtime_ns)
    except OSError:return None

def _fir_same(x,taps,torch):
    taps=[float(v) for v in (taps or [])][:128]
    if not taps:return x
    k=torch.tensor(taps,device=x.device,dtype=x.dtype)
    # causal FIR: y[n] = sum_k h[k] x[n-k]
    z=torch.nn.functional.conv1d(x[None,None],k.flip(0)[None,None],padding=k.numel()-1)[0,0]
    return z[:x.numel()]

def render_virtual_mics(mono,sample_rate:int,room_amount:float=.18,perspective:int=1,profile=None):
    torch=__import__('torch');x=mono.float();sr=max(8000,int(sample_rate));r=max(0.0,min(1.0,float(room_amount)))
    prof=profile if profile is not None else active_room_profile(); out=[]
    for i,(ms,air,early,pan) in enumerate(_DEFAULT_CFG):
        d=int(round(ms*sr/1000.0));y=_air(_delay(x,d,torch),air+r*.18,torch)
        if early>0:
            d2=d+int(round((4.0+1.7*(i%3))*sr/1000.0));y=y+_delay(x,d2,torch)*(early*(.45+.55*r))
        ent=(prof.get('feeds',{}).get(MIC_NAMES[i],{}) if prof else {})
        if ent:
            p_sr=int(prof.get('sample_rate',sr) or sr)
            extra=int(round(float(ent.get('delay_samples',0))*sr/max(1,p_sr)))
            y=_delay(y,max(0,extra),torch)*float(ent.get('gain',1.0))
            pan=float(ent.get('pan',pan))
        out.append((y,float(max(-1,min(1,pan))),ent))
    return out

def stereo_virtual_feeds(mono,sample_rate:int,room_amount:float=.18,perspective:int=1,profile=None):
    """Return [frames,32] ordered as 16 stereo pairs. Raw aux feeds ignore perspective weights."""
    torch=__import__('torch'); pairs=[]
    for y,pan,ent in render_virtual_mics(mono,sample_rate,room_amount,perspective,profile):
        if ent and (ent.get('left_fir') or ent.get('right_fir')):
            l=_fir_same(y,ent.get('left_fir') or [1.0],torch)
            r=_fir_same(y,ent.get('right_fir') or [1.0],torch)
        else:
            gl=math.sqrt(.5*(1-pan));gr=math.sqrt(.5*(1+pan));l=y*gl;r=y*gr
        pairs.append(torch.stack([l,r],-1))
    return torch.cat(pairs,-1)

def mix_virtual_stage(mono,sample_rate:int,room_amount:float=.18,perspective:int=1,profile=None):
    torch=__import__('torch'); feeds=stereo_virtual_feeds(mono,sample_rate,room_amount,perspective,profile)
    w=_PRESETS[max(0,min(3,int(perspective)))]
    left=torch.zeros_like(mono,dtype=torch.float32);right=torch.zeros_like(left);den=0.0
    for i,wi in enumerate(w):
        if wi<=0:continue
        left+=feeds[:,i*2]*(wi);right+=feeds[:,i*2+1]*(wi);den+=wi
    if den>0:left/=math.sqrt(den);right/=math.sqrt(den)
    return torch.stack([left,right],-1)

def render_stage_bundle(mono,sample_rate:int,room_amount:float=.18,perspective:int=1,profile=None):
    """Return [frames,34] = stereo master followed by 16 stereo virtual aux feeds."""
    torch=__import__('torch'); feeds=stereo_virtual_feeds(mono,sample_rate,room_amount,perspective,profile)
    w=_PRESETS[max(0,min(3,int(perspective)))]
    l=torch.zeros_like(mono,dtype=torch.float32);r=torch.zeros_like(l);den=0.0
    for i,wi in enumerate(w):
        if wi<=0:continue
        l+=feeds[:,2*i]*wi;r+=feeds[:,2*i+1]*wi;den+=wi
    if den>0:l/=math.sqrt(den);r/=math.sqrt(den)
    return torch.cat([torch.stack([l,r],-1),feeds],-1)
