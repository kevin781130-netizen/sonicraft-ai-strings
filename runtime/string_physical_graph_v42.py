"""SONICRAFT v4.2 String Physical Performance Graph.

Rule-based, strings-only performance planning. No learned acoustic technique is invented here.
The planner chooses a feasible string/fingering path, position shifts, bow state, pressure/contact,
portamento route and desk identity. These decisions remain editable/inspectable in the score graph.
"""
from __future__ import annotations
from dataclasses import asdict
from math import inf

# Low -> high open strings in MIDI note numbers.
OPEN_STRINGS={
    0:(55,62,69,76), # violin I G3 D4 A4 E5
    1:(55,62,69,76), # violin II
    2:(48,55,62,69), # viola C3 G3 D4 A4
    3:(36,43,50,57), # cello C2 G2 D3 A3
}
STRING_NAMES={
    0:("G","D","A","E"),
    1:("G","D","A","E"),
    2:("C","G","D","A"),
    3:("C","G","D","A"),
}
MAX_FINGER_SEMITONES={0:31,1:31,2:29,3:28}

PHYS_STRING=112
PHYS_POSITION=113
PHYS_BOW_DIRECTION=114
PHYS_BOW_CHANGE=115
PHYS_BOW_PRESSURE=116
PHYS_CONTACT_POINT=117
PHYS_PORTAMENTO=118
PHYS_DESK=119

def _is_short(n):
    return (n.end_tick-n.start_tick) <= 480 or n.base_art in (4,5,6,8)
def _is_legato(n):
    return bool(n.slur or (n.stack&2) or n.base_art in (1,2))
def _is_expressive(n):
    return bool((n.stack&8) or n.base_art in (3,11))

def feasible_fingerings(part,pitch):
    out=[]
    for s,open_pitch in enumerate(OPEN_STRINGS[part]):
        finger=int(pitch)-int(open_pitch)
        if 0<=finger<=MAX_FINGER_SEMITONES[part]:
            out.append((s,finger))
    return out

def _candidate_cost(n,s,finger,prev=None):
    # Lower cost is better. This is an ergonomic continuity model, not an acoustic-quality model.
    cost=0.0
    pos=finger/7.0
    cost += max(0.0,pos-2.5)*0.36
    if finger==0:
        if _is_expressive(n) or _is_legato(n): cost+=1.15
        elif _is_short(n) or n.base_art==8: cost-=0.40
    # Strongly expressive notes prefer a stopped string where vibrato is available.
    if _is_expressive(n) and finger<2: cost+=0.55
    if prev is not None:
        ps,pf=prev
        shift=abs(finger-pf)
        string_cross=abs(s-ps)
        cost += min(2.4,shift*0.115)
        cost += string_cross*0.34
        # Under slur, large shifts/crossings are more expensive.
        if _is_legato(n):
            cost += max(0,shift-5)*0.12 + string_cross*0.25
        # Prefer staying in a coherent hand frame.
        if s==ps and shift<=4: cost-=0.22
    # Avoid unnecessarily high strings for very low finger positions when a neighboring stopped option exists.
    cost += s*0.018
    return cost

def choose_fingering_path(notes,part):
    if not notes:return
    candidates=[feasible_fingerings(part,n.pitch) for n in notes]
    for i,c in enumerate(candidates):
        if not c:
            # Keep manifest honest. Fallback is only a graph placeholder.
            candidates[i]=[(0,max(0,notes[i].pitch-OPEN_STRINGS[part][0]))]
            notes[i].physical_warnings.append("pitch_outside_configured_string_range")
    dp=[];back=[]
    for i,(n,cands) in enumerate(zip(notes,candidates)):
        row=[];br=[]
        for j,c in enumerate(cands):
            if i==0:
                row.append(_candidate_cost(n,*c,None));br.append(-1)
            else:
                best=inf;bestk=0
                for k,prev in enumerate(candidates[i-1]):
                    v=dp[i-1][k]+_candidate_cost(n,*c,prev)
                    if v<best:best=v;bestk=k
                row.append(best);br.append(bestk)
        dp.append(row);back.append(br)
    j=min(range(len(dp[-1])),key=lambda k:dp[-1][k])
    path=[None]*len(notes)
    for i in range(len(notes)-1,-1,-1):
        path[i]=candidates[i][j]
        j=back[i][j] if i else 0
    prev=None
    for n,(s,finger) in zip(notes,path):
        n.string_index=s
        n.string_name=STRING_NAMES[part][s]
        n.finger_semitone=finger
        n.position_index=0 if finger==0 else max(1,1+(finger-1)//4)
        n.open_string=(finger==0)
        n.shift_semitones=0 if prev is None else finger-prev[1]
        prev=(s,finger)

def plan_bowing(notes):
    if not notes:return
    direction=0 # 0 down, 1 up
    prev=None
    for n in notes:
        gap=10**9 if prev is None else n.start_tick-prev.end_tick
        legato_link=prev is not None and gap<=40 and (_is_legato(prev) or _is_legato(n))
        forced_down="down-bow" in n.technical
        forced_up="up-bow" in n.technical
        if forced_down: direction=0
        elif forced_up: direction=1
        elif prev is None or gap>=960:
            direction=0
        elif not legato_link:
            direction=1-direction
        n.bow_direction=direction
        n.bow_change=bool(forced_down or forced_up or not legato_link)
        # Pizzicato has no bowed-pressure/contact interpretation.
        if n.base_art==8:
            n.bow_pressure=0.0;n.contact_point=0.5;n.bow_change=False
        else:
            dyn=max(1,min(127,n.cc1))/127.0
            pressure=.30+.46*dyn
            if n.stack&1 or n.base_art==4:pressure+=.12
            if n.base_art in (5,6):pressure+=.05
            if _is_expressive(n):pressure-=.06
            n.bow_pressure=max(.08,min(.95,pressure))
            contact=.48
            if n.base_art==7:contact+=.12
            if n.stack&1 or n.base_art==4:contact+=.08
            if n.base_art==11:contact-=.22
            if _is_expressive(n):contact-=.08
            n.contact_point=max(.08,min(.92,contact))
        prev=n

def plan_portamento(notes):
    prev=None
    for n in notes:
        route=0.0
        if prev is not None:
            interval=abs(n.pitch-prev.pitch)
            shift=abs(n.shift_semitones)
            connected=(n.start_tick-prev.end_tick)<=40
            if n.base_art==2:
                route=1.0
            elif connected and _is_legato(n) and shift>=5:
                route=min(.82,.18+.07*shift+.025*interval)
            elif connected and _is_legato(n) and interval>=7:
                route=.28
        n.portamento_route=max(0.0,min(1.0,route))
        prev=n

def plan_string_physics(g):
    # Plan independently inside each explicit v4.1 voice lane.
    by_lane={}
    for n in g.notes:
        by_lane.setdefault((n.part,n.lane_channel),[]).append(n)
    for (part,lane),notes in by_lane.items():
        notes.sort(key=lambda n:(n.start_tick,n.pitch))
        choose_fingering_path(notes,part)
        plan_bowing(notes)
        plan_portamento(notes)
        # Stable desk identity comes from the explicit voice lane within the string part.
        channels={0:(0,4,5,6),1:(1,7,8,9),2:(2,10,11,12),3:(3,13,14,15)}
        desk=channels[part].index(lane) if lane in channels[part] else 0
        for n in notes:n.divisi_desk=desk
    return g

def physical_note_dict(n):
    return {
        "string_index":n.string_index,"string_name":n.string_name,
        "finger_semitone":n.finger_semitone,"position_index":n.position_index,
        "shift_semitones":n.shift_semitones,"open_string":n.open_string,
        "bow_direction":"down" if n.bow_direction==0 else "up",
        "bow_change":n.bow_change,"bow_pressure":round(float(n.bow_pressure),6),
        "contact_point":round(float(n.contact_point),6),
        "portamento_route":round(float(n.portamento_route),6),
        "divisi_desk":n.divisi_desk,
        "warnings":list(n.physical_warnings),
    }
