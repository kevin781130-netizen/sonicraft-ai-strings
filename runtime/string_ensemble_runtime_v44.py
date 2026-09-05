"""SONICRAFT v4.4 runtime execution for score-authored ensemble timing.

CC36 / opcode 120 = signed Attack Offset (-8..+8 ms, normalized 0..1)
CC37 / opcode 121 = Phrase Breath (0..20 ms, normalized 0..1)

The helper shifts render-event timing only when these explicit v4.4 control events are present.
Legacy v4.3/v4.2/v4.1 event lists are returned unchanged.
"""
from __future__ import annotations

ENSEMBLE_ATTACK_OPCODE=120
ENSEMBLE_BREATH_OPCODE=121
ATTACK_MAX_MS=8.0
BREATH_MAX_MS=20.0

def apply_ensemble_event_timing_v44(events,sample_rate):
    recognized=any(int(e.get("type",0))==4 and int(e.get("note",-1)) in
                   (ENSEMBLE_ATTACK_OPCODE,ENSEMBLE_BREATH_OPCODE) for e in events)
    if not recognized:
        return events
    sr=max(8000.0,float(sample_rate))
    attack=.5;breath=0.0
    out=[];active_on={}
    for src in sorted(events,key=lambda e:(int(e.get("project_sample",0)),0 if int(e.get("type",0))==4 else 1)):
        typ=int(src.get("type",0));code=int(src.get("note",-1))
        if typ==4 and code==ENSEMBLE_ATTACK_OPCODE:
            attack=max(0.0,min(1.0,float(src.get("velocity",.5))))
            out.append(src);continue
        if typ==4 and code==ENSEMBLE_BREATH_OPCODE:
            breath=max(0.0,min(1.0,float(src.get("velocity",0.0))))
            out.append(src);continue
        e=dict(src);ps=int(e.get("project_sample",0))
        if typ==1:
            delta_ms=(attack-.5)*2.0*ATTACK_MAX_MS
            ps+=int(round(delta_ms*.001*sr))
            e["project_sample"]=ps
            active_on[int(e.get("note",-1))]=ps
        elif typ==2:
            shorten_ms=breath*BREATH_MAX_MS
            ps-=int(round(shorten_ms*.001*sr))
            on=active_on.get(int(e.get("note",-1)))
            if on is not None:ps=max(on+1,ps)
            e["project_sample"]=ps
        out.append(e)
    return sorted(out,key=lambda e:(int(e.get("project_sample",0)),0 if int(e.get("type",0))==4 else 1))

def attack_norm_from_ms(ms):
    return max(0.0,min(1.0,.5+float(ms)/(2.0*ATTACK_MAX_MS)))

def breath_norm_from_ms(ms):
    return max(0.0,min(1.0,float(ms)/BREATH_MAX_MS))
