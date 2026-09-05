"""SONICRAFT v1.8 frontier score context.

Parameter-free feature extraction for the tiny learned context adapter.  It never edits
written MIDI/CC.  The adapter only receives hidden ensemble / phrase state.

The important deployment trick is look-back: render requests may contain events before
``start_sample`` while the requested audio range is unchanged.  That lets the renderer
recover sustained notes, previous intervals and phrase age without a stateful project ID.
"""
from __future__ import annotations
import numpy as np


def _idx(sample, start, sr, fps, n):
    return int(max(0, min(n - 1, round((int(sample) - int(start)) / float(sr) * int(fps)))))


def _smooth(x, width=5):
    x=np.asarray(x,dtype=np.float32)
    if x.size < width or width <= 1: return x
    k=np.ones(int(width),np.float32)/float(width)
    return np.convolve(x,k,mode='same').astype(np.float32)


def _score_state(events,start_sample,end_sample,sample_rate,fps=100):
    dur=max(.08,(int(end_sample)-int(start_sample))/float(sample_rate)); n=max(8,int(np.ceil(dur*fps)))
    gate=np.zeros((4,n),np.float32); pitch=np.zeros((4,n),np.float32); onset=np.zeros((4,n),np.float32)
    active=[None]*4; notes=[[] for _ in range(4)]
    ordered=sorted(events,key=lambda e:int(e.get('project_sample',0)))
    for e in ordered:
        p=int(e.get('part',-1)); typ=int(e.get('type',0)); ps=int(e.get('project_sample',start_sample))
        if p<0 or p>=4 or typ not in (1,2): continue
        # Process look-back events rather than clamping them into fake onsets at frame zero.
        if typ==1:
            if active[p] is not None:
                a,note,real_on=active[p]; b=0 if ps<int(start_sample) else _idx(ps,start_sample,sample_rate,fps,n)
                if b>a: gate[p,a:b]=1.; pitch[p,a:b]=float(note)
            a=0 if ps<int(start_sample) else _idx(ps,start_sample,sample_rate,fps,n)
            active[p]=(a,int(e.get('note',0)),ps)
            notes[p].append({'on_sample':ps,'on':a,'note':int(e.get('note',0)),'off_sample':None})
            if ps>=int(start_sample) and ps<int(end_sample): onset[p,a:min(n,a+2)]=1.
        else:
            if active[p] is not None:
                a,note,real_on=active[p]; b=0 if ps<int(start_sample) else _idx(ps,start_sample,sample_rate,fps,n)
                b=max(a,min(n,b))
                if b>a: gate[p,a:b]=1.; pitch[p,a:b]=float(note)
                # Match the most recent open note in the compact history.
                for q in reversed(notes[p]):
                    if q['off_sample'] is None: q['off_sample']=ps; break
                active[p]=None
    for p in range(4):
        if active[p] is not None:
            a,note,_=active[p]; gate[p,a:]=1.; pitch[p,a:]=float(note)
    return gate,pitch,onset,notes,n


def phrase_position_curve(events,part,start_sample,end_sample,sample_rate,bpm,fps=100):
    """Tempo-aware phrase age derived from actual note/rest history, not request position."""
    gate,pitch,onset,notes,n=_score_state(events,start_sample,end_sample,sample_rate,fps)
    p=max(0,min(3,int(part))); sec_per_beat=60.0/max(24.0,float(bpm)); break_s=.75*sec_per_beat
    # Determine phrase start by walking chronological notes including look-back events.
    ns=sorted(notes[p],key=lambda q:q['on_sample'])
    phrase_start=int(start_sample); prev_off=None
    for q in ns:
        on=int(q['on_sample']); off=q['off_sample']
        if on>=int(end_sample): break
        if prev_off is None or (on-int(prev_off))/float(sample_rate)>break_s:
            phrase_start=on
        if off is not None: prev_off=int(off)
    t=int(start_sample)+np.arange(n,dtype=np.float64)/float(fps)*float(sample_rate)
    age=np.maximum(0.0,(t-float(phrase_start))/float(sample_rate))/max(sec_per_beat*8.0,1e-6)
    return np.clip(age,0.0,1.0).astype(np.float32)


def frontier_context_curves(events,part,start_sample,end_sample,sample_rate,bpm,
                            dynamics=None,vibrato=None,legato=None,fps=100):
    """Return 14 hidden context curves [14, frames] in bounded ranges.

    Features: other-density, synchronized entry, support/top role, relative register,
    motion agreement, phrase age, onset age, previous/next interval, dynamics/vibrato
    trend, authored legato state and re-entry-after-rest.
    """
    gate,pitch,onset,notes,n=_score_state(events,start_sample,end_sample,sample_rate,fps)
    p=max(0,min(3,int(part))); others=[q for q in range(4) if q!=p]
    other_gate=gate[others]; density=_smooth(np.clip(other_gate.sum(0)/3.,0,1))
    radius=max(1,int(round(.050*fps))); sync=np.zeros(n,np.float32)
    current_on=np.flatnonzero(onset[p]>0); other_on=[np.flatnonzero(onset[q]>0) for q in others]
    for i in current_on:
        hits=sum(bool(np.any(np.abs(v-int(i))<=radius)) for v in other_on)
        if hits: sync[max(0,i-1):min(n,i+3)]=np.maximum(sync[max(0,i-1):min(n,i+3)],hits/3.)
    own=pitch[p]; op=pitch[others]; maxo=op.max(0); active=gate[p]>0
    support=_smooth((active & (maxo>own)).astype(np.float32)); top=_smooth((active & ((maxo<=own)|(maxo==0))).astype(np.float32))
    denom=np.maximum(1.,other_gate.sum(0)); meano=(op*other_gate).sum(0)/denom
    reg=np.clip((own-meano)/24.,-1,1).astype(np.float32); reg[~active]=0
    dm=np.diff(pitch,prepend=pitch[:,:1],axis=1); own_dir=np.sign(dm[p]); other_dir=np.sign(dm[others]).sum(0)
    motion=_smooth(np.where((own_dir!=0)&(other_dir!=0),(np.sign(other_dir)==own_dir).astype(np.float32)*2-1,0).astype(np.float32))

    phrase=phrase_position_curve(events,p,start_sample,end_sample,sample_rate,bpm,fps)
    sec_per_beat=60./max(24.,float(bpm)); onset_age=np.ones(n,np.float32)
    last=-10**9
    for i in range(n):
        if onset[p,i]>0: last=i
        onset_age[i]=min(1.,max(0.,(i-last)/float(fps)/max(2*sec_per_beat,1e-6))) if last>-10**8 else 1.

    prev_int=np.zeros(n,np.float32); next_int=np.zeros(n,np.float32); reentry=np.zeros(n,np.float32)
    ns=sorted(notes[p],key=lambda q:q['on_sample']); break_samples=int(.75*sec_per_beat*float(sample_rate))
    for j,q in enumerate(ns):
        a=0 if int(q['on_sample'])<int(start_sample) else _idx(q['on_sample'],start_sample,sample_rate,fps,n)
        b=n
        if q['off_sample'] is not None and int(q['off_sample'])<int(end_sample): b=max(a+1,_idx(q['off_sample'],start_sample,sample_rate,fps,n))
        if j: prev_int[a:b]=np.clip((int(q['note'])-int(ns[j-1]['note']))/24.,-1,1)
        if j+1<len(ns): next_int[a:b]=np.clip((int(ns[j+1]['note'])-int(q['note']))/24.,-1,1)
        if j and ns[j-1]['off_sample'] is not None and int(q['on_sample'])-int(ns[j-1]['off_sample'])>break_samples and int(q['on_sample'])>=int(start_sample):
            reentry[a:min(n,a+max(2,int(.08*fps)))]=1.

    def arr(x,default):
        if x is None: return np.full(n,float(default),np.float32)
        x=np.asarray(x,dtype=np.float32).reshape(-1)
        if len(x)==n:return x
        if len(x)<=1:return np.full(n,float(x[0]) if len(x) else float(default),np.float32)
        xp=np.linspace(0,1,len(x)); return np.interp(np.linspace(0,1,n),xp,x).astype(np.float32)
    dyn=arr(dynamics,.6); vib=arr(vibrato,.0); leg=arr(legato,1.)
    dyn_tr=np.clip(np.gradient(_smooth(dyn))*8.,-1,1).astype(np.float32)
    vib_tr=np.clip(np.gradient(_smooth(vib))*8.,-1,1).astype(np.float32)
    ctx=np.stack([density,sync,support,top,reg,motion,phrase,onset_age,prev_int,next_int,dyn_tr,vib_tr,np.clip(leg,0,1),reentry],0)
    return ctx.astype(np.float32),phrase
