"""Deterministic independent-voice allocator for overlapping notes."""
from __future__ import annotations

def allocate_polyphonic_event_lanes(events, part:int, max_voices:int=16):
    """Split one part into independent monophonic lanes while duplicating control/reset events.

    Note-off is paired with the oldest active matching pitch. Excess voices steal the oldest lane
    deterministically, so behavior is bounded and repeatable.
    """
    pe=[dict(e) for e in sorted(events,key=lambda x:(int(x['project_sample']),int(x['type']))) if int(e.get('part',-1))==part or int(e.get('type',0))==5]
    explicit=[e for e in pe if int(e.get('voice_lane',-1))>=0 and int(e.get('type',0)) in (1,2,3,4)]
    if explicit:
        lane_ids=sorted({int(e.get('voice_lane',-1)) for e in explicit if 0<=int(e.get('voice_lane',-1))<max_voices})
        out=[]
        global_controls=[e for e in pe if int(e.get('type',0))==5 and int(e.get('voice_lane',-1))<0]
        for lane_id in lane_ids:
            lane_events=[e for e in pe if int(e.get('voice_lane',-1))==lane_id]
            notes=[e for e in lane_events if int(e.get('type',0)) in (1,2)]
            if not notes:
                continue
            merged=sorted(global_controls+[e for e in lane_events if int(e.get('type',0)) in (1,2,3,4)],
                          key=lambda x:(int(x['project_sample']),0 if int(x['type']) in (3,4,5) else 1))
            out.append(merged)
        return out

    controls=[e for e in pe if int(e.get('type',0)) in (3,4,5)]
    lanes=[[] for _ in range(max(1,int(max_voices)))]
    active={}  # pitch -> [(lane,on_sample)]
    lane_free=[True]*len(lanes)
    lane_started=[None]*len(lanes)
    note_events=[e for e in pe if int(e.get('type',0)) in (1,2)]
    for e in note_events:
        typ=int(e['type']); pitch=int(e.get('note',0)); ps=int(e['project_sample'])
        if typ==1:
            free=next((i for i,v in enumerate(lane_free) if v),None)
            if free is None:
                free=min(range(len(lanes)),key=lambda i:(lane_started[i] if lane_started[i] is not None else 1<<62,i))
                # Inject a safe note-off for any stolen notes in that lane.
                for p,items in list(active.items()):
                    kept=[]
                    for ln,on in items:
                        if ln==free:
                            off=dict(e);off['type']=2;off['note']=p;off['velocity']=0.0;lanes[ln].append(off)
                        else: kept.append((ln,on))
                    if kept:active[p]=kept
                    else:active.pop(p,None)
            lanes[free].append(e);lane_free[free]=False;lane_started[free]=ps
            active.setdefault(pitch,[]).append((free,ps))
        else:
            items=active.get(pitch,[])
            if not items: continue
            items.sort(key=lambda x:(x[1],x[0])); ln,_=items.pop(0);lanes[ln].append(e);lane_free[ln]=True;lane_started[ln]=None
            if items:active[pitch]=items
            else:active.pop(pitch,None)
    out=[]
    for ln,note_lane in enumerate(lanes):
        if not note_lane:continue
        first=min(int(x['project_sample']) for x in note_lane); last=max(int(x['project_sample']) for x in note_lane)
        relevant=[c for c in controls if int(c['project_sample'])<=last or int(c.get('type',0))==5]
        merged=sorted(relevant+note_lane,key=lambda x:(int(x['project_sample']),0 if int(x['type']) in (3,4,5) else 1))
        out.append(merged)
    return out
