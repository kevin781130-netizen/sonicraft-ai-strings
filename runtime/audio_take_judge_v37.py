"""SONICRAFT v3.7 audio-aware A/B/C/D Take Judge.

Dependency: NumPy only. No learned preference model is used.
Scores are engineering/score-adherence diagnostics, not a claim of musical taste.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np

@dataclass(frozen=True)
class TakeJudgeScore:
    overall: float
    dynamics: float
    attack: float
    transition: float
    stability: float
    safety: float
    peak: float

def _mono(audio):
    x=np.asarray(audio,np.float32)
    if x.ndim==1: return x
    if x.ndim!=2 or x.shape[1]<1: raise ValueError("audio must be [frames] or [frames,channels]")
    # Judge the master stereo only. Multi-out room geometry must not double-weight a take.
    y=x[:,:min(2,x.shape[1])]
    return np.mean(y,axis=1,dtype=np.float32)

def _frame_rms(x,frame,hop):
    if len(x)<frame:
        z=np.pad(x,(0,max(0,frame-len(x))))
        return np.asarray([np.sqrt(np.mean(z*z)+1e-12)],np.float32)
    n=1+(len(x)-frame)//hop
    out=np.empty(n,np.float32)
    for i in range(n):
        q=x[i*hop:i*hop+frame]
        out[i]=np.sqrt(np.mean(q*q)+1e-12)
    return out

def _expected_dynamics(events,start,end,nframes):
    """Piecewise authored CC1/control intent, normalized only for contour comparison."""
    if nframes<=0:return np.zeros(0,np.float32)
    pts=[]
    for e in sorted(events,key=lambda z:int(z.get('project_sample',0))):
        ps=int(e.get('project_sample',0))
        if ps>end:break
        c=e.get('controls') or ()
        if len(c)>0 and ps<=end:
            pts.append((max(start,ps),float(c[0])))
    base=.62
    # Find last authored dynamic before start.
    for e in sorted(events,key=lambda z:int(z.get('project_sample',0))):
        ps=int(e.get('project_sample',0))
        if ps>start:break
        c=e.get('controls') or ()
        if len(c)>0:base=float(c[0])
    out=np.full(nframes,base,np.float32)
    span=max(1,end-start)
    for ps,v in pts:
        idx=max(0,min(nframes-1,int((ps-start)/span*nframes)))
        out[idx:]=v
    return out

def _contour_score(measured,expected):
    m=np.asarray(measured,np.float64); e=np.asarray(expected,np.float64)
    n=min(len(m),len(e))
    if n<2:return 1.0
    m=m[:n];e=e[:n]
    # Log energy better matches perceived dynamics and avoids absolute-gain bias.
    m=np.log(np.maximum(m,1e-7))
    m=(m-m.mean())/(m.std()+1e-6)
    e=(e-e.mean())/(e.std()+1e-6)
    if np.std(e)<1e-5:return float(np.clip(1.0-np.std(m)*.12,0,1))
    corr=float(np.clip(np.dot(m,e)/max(1,n),-1,1))
    rmse=float(np.sqrt(np.mean((m-e)**2)))
    return float(np.clip(.65*((corr+1)*.5)+.35*(1-rmse/2.5),0,1))

def _attack_score(x,events,start,end,sr):
    onsets=sorted({int(e.get('project_sample',0))-start for e in events
                   if int(e.get('type',0))==1 and start<=int(e.get('project_sample',0))<end})
    if not onsets:return 1.0
    pre=max(8,int(sr*.012)); post=max(16,int(sr*.055))
    rises=[]
    for o in onsets:
        a=max(0,o-pre); b=min(len(x),o+post)
        if b-a<8:continue
        pre_r=np.sqrt(np.mean(x[a:max(a+1,min(o,b))]**2)+1e-12)
        post_r=np.sqrt(np.mean(x[max(a,o):b]**2)+1e-12)
        rises.append(float((post_r+1e-6)/(pre_r+1e-6)))
    if not rises:return 1.0
    r=np.log1p(np.asarray(rises,np.float64))
    med=np.median(r)
    mad=np.median(np.abs(r-med))+1e-6
    outlier=np.mean(np.clip(np.abs(r-med)/(4*mad),0,1))
    weak=np.mean(r<math.log1p(1.08))
    return float(np.clip(1-.62*outlier-.38*weak,0,1))

def _transition_score(x,events,start,end,sr):
    # Penalize unexplained derivative bursts away from authored note onsets.
    d=np.abs(np.diff(x,prepend=x[:1]))
    if len(d)<8:return 1.0
    mask=np.ones(len(d),dtype=bool)
    radius=max(4,int(sr*.035))
    for e in events:
        if int(e.get('type',0))!=1:continue
        o=int(e.get('project_sample',0))-start
        if 0<=o<len(d):
            mask[max(0,o-radius):min(len(d),o+radius)]=False
    q=d[mask] if np.any(mask) else d
    p95=float(np.percentile(q,95)); p999=float(np.percentile(q,99.9))
    burst_ratio=p999/(p95+1e-7)
    burst_score=float(np.clip(1-(burst_ratio-2.2)/8.0,0,1))
    # Broad-band chatter can be consistently "spiky" and evade a percentile-ratio test.
    # Derivative energy relative to signal RMS catches that without requiring FFTs.
    q_rms=float(np.sqrt(np.mean(q*q)+1e-12))
    x_rms=float(np.sqrt(np.mean(x*x)+1e-12))
    derivative_ratio=q_rms/(x_rms+1e-7)
    rough_score=float(np.clip(1-(derivative_ratio-.06)/.34,0,1))
    return float(np.clip(.55*burst_score+.45*rough_score,0,1))

def _stability_score(x,sr):
    rms=_frame_rms(x,max(32,int(sr*.040)),max(16,int(sr*.020)))
    active=rms[rms>max(1e-5,float(np.percentile(rms,20))*.75)]
    if len(active)<3:return 1.0
    log=np.log(np.maximum(active,1e-7))
    # Allow expressive motion; only penalize extreme short-window volatility.
    diff=np.diff(log)
    volatility=float(np.median(np.abs(diff)))
    return float(np.clip(1-volatility/.48,0,1))

def _safety_score(x):
    peak=float(np.max(np.abs(x))) if len(x) else 0.0
    near=float(np.mean(np.abs(x)>.965)) if len(x) else 0.0
    # Peak below 0.94 is full score; near-clipped sample density adds a stronger penalty.
    peak_pen=max(0.0,(peak-.94)/.06)
    return float(np.clip(1-.55*peak_pen-.45*min(1.0,near/.0025),0,1)),peak

def judge_take(audio,sample_rate,events,start_sample,end_sample)->TakeJudgeScore:
    sr=max(8000,int(sample_rate)); x=_mono(audio)
    if not np.isfinite(x).all(): return TakeJudgeScore(0,0,0,0,0,0,float('inf'))
    frame=max(32,int(sr*.050));hop=max(16,int(sr*.025))
    measured=_frame_rms(x,frame,hop)
    expected=_expected_dynamics(events,start_sample,end_sample,len(measured))
    dynamics=_contour_score(measured,expected)
    attack=_attack_score(x,events,start_sample,end_sample,sr)
    transition=_transition_score(x,events,start_sample,end_sample,sr)
    stability=_stability_score(x,sr)
    safety,peak=_safety_score(x)
    # Score adherence/robustness weights. Subjective timbre preference is intentionally absent.
    overall=.29*dynamics+.23*attack+.20*transition+.16*stability+.12*safety
    return TakeJudgeScore(*(float(np.clip(v,0,1)) for v in (overall,dynamics,attack,transition,stability,safety)),float(peak))

def rank_takes(audios,sample_rate,events,start_sample,end_sample,favorite_mask=0,reject_mask=0):
    if len(audios)!=4: raise ValueError("expected A/B/C/D audio")
    scores=[judge_take(a,sample_rate,events,start_sample,end_sample) for a in audios]
    best=-1;best_rank=-1e9
    for i,s in enumerate(scores):
        bit=1<<i
        if reject_mask&bit:continue
        rank=s.overall+(1.25 if favorite_mask&bit else 0.0)
        if rank>best_rank:best_rank=rank;best=i
    return best,scores

def score_dict(score:TakeJudgeScore):
    return asdict(score)
