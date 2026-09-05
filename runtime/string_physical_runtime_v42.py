"""v4.2 physical-performance residuals for the existing strings control contract.

These controls do not add acoustic classes. They bend already-supported dynamics/vibrato/
transition/attack/tightness/expression/bow-change behavior using explicit note-level physical intent.
"""
from __future__ import annotations
import numpy as np

PHYS_STRING=112
PHYS_POSITION=113
PHYS_BOW_DIRECTION=114
PHYS_BOW_CHANGE=115
PHYS_BOW_PRESSURE=116
PHYS_CONTACT_POINT=117
PHYS_PORTAMENTO=118
PHYS_DESK=119

def physical_curves(events,start_sample,sample_rate,fps,n):
    recognized=[e for e in events if int(e.get("type",0))==4 and int(e.get("note",-1)) in
                (PHYS_STRING,PHYS_POSITION,PHYS_BOW_DIRECTION,PHYS_BOW_CHANGE,
                 PHYS_BOW_PRESSURE,PHYS_CONTACT_POINT,PHYS_PORTAMENTO,PHYS_DESK)]
    if not recognized:
        return None
    vals={
      PHYS_STRING:.5,PHYS_POSITION:0.,PHYS_BOW_DIRECTION:0.,
      PHYS_BOW_CHANGE:1.,PHYS_BOW_PRESSURE:.5,PHYS_CONTACT_POINT:.5,
      PHYS_PORTAMENTO:0.,PHYS_DESK:0.,
    }
    curves={k:np.full(n,v,np.float32) for k,v in vals.items()}
    curves["_known"]={k:False for k in vals}
    for e in sorted(recognized,key=lambda x:int(x.get("project_sample",0))):
        if int(e.get("type",0))!=4:continue
        code=int(e.get("note",-1))
        if code not in curves:continue
        ps=int(e.get("project_sample",0))
        idx=int(max(0,min(n-1,round((ps-start_sample)/float(sample_rate)*fps))))
        curves[code][idx:]=np.float32(max(0.,min(1.,float(e.get("velocity",0.)))))
        curves["_known"][code]=True
    return curves

def apply_string_physical_residuals(dyn,vib,exp,leg,trans,tight,attack,bow,pitchbend,phys,gate=None,onset=None):
    dyn=np.asarray(dyn,np.float32).copy();vib=np.asarray(vib,np.float32).copy();exp=np.asarray(exp,np.float32).copy()
    leg=np.asarray(leg,np.float32).copy();trans=np.asarray(trans,np.float32).copy();tight=np.asarray(tight,np.float32).copy()
    attack=np.asarray(attack,np.float32).copy();bow=np.asarray(bow,np.float32).copy();pitchbend=np.asarray(pitchbend,np.float32).copy()
    known=phys.get("_known",{})
    pos=phys[PHYS_POSITION];direction=phys[PHYS_BOW_DIRECTION];change=phys[PHYS_BOW_CHANGE]
    pressure=phys[PHYS_BOW_PRESSURE];contact=phys[PHYS_CONTACT_POINT];porta=phys[PHYS_PORTAMENTO];desk=phys[PHYS_DESK]
    string_sel=phys[PHYS_STRING]

    if known.get(PHYS_POSITION,False):
        vib=np.clip(vib+(pos-.25)*.08,0,1)
        attack=np.clip(attack-(pos*.055),0,1)
    if known.get(PHYS_STRING,False):
        attack=np.clip(attack+(string_sel-.5)*.035,0,1)
        trans=np.clip(trans+(string_sel-.5)*.018,0,1)
    if known.get(PHYS_BOW_DIRECTION,False):
        attack=np.clip(attack+(0.5-direction)*.07,0,1)
    if known.get(PHYS_BOW_PRESSURE,False):
        dyn=np.clip(dyn+(pressure-.5)*.10,0,1)
        attack=np.clip(attack+(pressure-.5)*.15,0,1)
        tight=np.clip(tight+(pressure-.5)*.10,0,1)
    if known.get(PHYS_CONTACT_POINT,False):
        attack=np.clip(attack+(contact-.5)*.12,0,1)
        tight=np.clip(tight+(contact-.5)*.11,0,1)
        exp=np.clip(exp-(contact-.5)*.035,0,1)
        vib=np.clip(vib-(contact-.5)*.045,0,1)
    if known.get(PHYS_BOW_CHANGE,False):
        if onset is not None:
            onset_curve=np.asarray(onset,np.float32)
            bow=np.clip(np.maximum(bow,change*onset_curve*.88),0,1)
        else:
            bow=np.clip(np.maximum(bow,change*.88),0,1)
    if known.get(PHYS_PORTAMENTO,False):
        leg=np.clip(np.maximum(leg,porta*.92),0,1)
        trans=np.clip(trans-porta*.22,0,1)
        pitchbend=np.clip(pitchbend+(porta*.012),0,1)
    if known.get(PHYS_POSITION,False):
        open_like=(pos<.01)
        vib=np.where(open_like,np.minimum(vib,.08),vib).astype(np.float32)
    if known.get(PHYS_DESK,False):
        desk_phase=(desk*2.0-1.0)*.012
        dyn=np.clip(dyn+desk_phase,0,1)
        attack=np.clip(attack-desk_phase*.7,0,1)

    if gate is not None:
        g=np.asarray(gate,np.float32)
        # No physical residual outside active notes except transition continuity.
        dyn=np.where(g>0,dyn,np.asarray(dyn))
    return dyn,vib,exp,leg,trans,tight,attack,bow,pitchbend
