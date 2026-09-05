"""v4.5 opt-in continuous gesture interpolation.

Opcode 122 / CC38 enables a gesture window on one explicit String Voice lane.
CC39 is lane-local micro pitch centered at .5, mapped to +/-50 cents by the compiler.
Legacy material with no opcode 122 is returned unchanged.
"""
from __future__ import annotations
import numpy as np

GESTURE_AMOUNT_OPCODE=122
GESTURE_MAX_MICRO_CENTS=50.0

def gesture_windows_v45(events,start_sample,end_sample):
    out=[];active=None;amount=0.0
    for e in sorted(events,key=lambda x:int(x.get('project_sample',0))):
        if int(e.get('type',0))!=4 or int(e.get('note',-1))!=GESTURE_AMOUNT_OPCODE:continue
        ps=int(e.get('project_sample',0));v=max(0.0,min(1.0,float(e.get('velocity',0.0))))
        if v>0 and active is None:active=ps;amount=v
        elif v>0:amount=max(amount,v)
        elif active is not None:
            out.append((max(int(start_sample),active),min(int(end_sample),ps),amount));active=None;amount=0.0
    if active is not None:out.append((max(int(start_sample),active),int(end_sample),amount))
    return [(a,b,m) for a,b,m in out if b>a and m>0]

def _idx(ps,start,sr,fps,n):return int(max(0,min(n-1,round((int(ps)-int(start))/float(sr)*fps))))

def smooth_voice_controls_v45(events,start_sample,end_sample,sr,fps,arrays):
    windows=gesture_windows_v45(events,start_sample,end_sample)
    if not windows:return arrays
    out=[np.asarray(a,np.float32).copy() for a in arrays]
    # code==0 are ordinary per-lane control snapshots from CC22/23/24/25/26/39 etc.
    controls=[e for e in events if int(e.get('type',0))==4 and int(e.get('note',-1))==0 and e.get('controls')]
    if not controls:return out
    for wa,wb,amount in windows:
        pts={}
        for e in controls:
            ps=int(e.get('project_sample',0))
            if wa<=ps<=wb:pts[_idx(ps,start_sample,sr,fps,len(out[0]))]=list(e['controls'])
        if len(pts)<2:continue
        xs=sorted(pts)
        ia=_idx(wa,start_sample,sr,fps,len(out[0]));ib=_idx(wb,start_sample,sr,fps,len(out[0]))
        grid=np.arange(ia,ib+1,dtype=np.float32)
        # controls vector indices matching arrays passed by callers.
        cidx=(0,1,2,6,8,10,11,12,13)
        for oi,ci in enumerate(cidx):
            xp=np.asarray(xs,dtype=np.float32);yp=np.asarray([pts[x][ci] for x in xs],dtype=np.float32)
            interp=np.interp(grid,xp,yp).astype(np.float32)
            base=out[oi][ia:ib+1]
            out[oi][ia:ib+1]=base*(1.0-amount)+interp*amount
    return out

def smooth_physical_curves_v45(phys,events,start_sample,end_sample,sr,fps):
    windows=gesture_windows_v45(events,start_sample,end_sample)
    if phys is None or not windows:return phys
    known=dict(phys.get('_known',{}))
    out={k:np.asarray(v,np.float32).copy() for k,v in phys.items() if k!='_known'}
    out['_known']=known
    numeric=[v for k,v in out.items() if k!='_known']
    n=len(numeric[0])
    for code,curve in list(out.items()):
        if code=='_known':continue
        ev=[e for e in events if int(e.get('type',0))==4 and int(e.get('note',-1))==int(code)]
        if len(ev)<2:continue
        for wa,wb,amount in windows:
            pts={_idx(e['project_sample'],start_sample,sr,fps,n):max(0.0,min(1.0,float(e.get('velocity',0.0)))) for e in ev if wa<=int(e.get('project_sample',0))<=wb}
            if len(pts)<2:continue
            xs=sorted(pts);ia=_idx(wa,start_sample,sr,fps,n);ib=_idx(wb,start_sample,sr,fps,n)
            grid=np.arange(ia,ib+1,dtype=np.float32)
            interp=np.interp(grid,np.asarray(xs,np.float32),np.asarray([pts[x] for x in xs],np.float32)).astype(np.float32)
            curve[ia:ib+1]=curve[ia:ib+1]*(1.0-amount)+interp*amount
    return out

def micro_pitch_norm_from_cents(cents):
    return max(0.0,min(1.0,.5+float(cents)/(2.0*GESTURE_MAX_MICRO_CENTS)))
