"""SONICRAFT v4.7 Phrase-Level Bow Energy & Vibrato Continuity Graph.

Builds long-line performance arcs on top of v4.6 transition-linked chains.
No new MIDI CC is required. A v4.7 phrase is marked by a tiny CC38 sentinel (1/127)
immediately before the normal CC38 Gesture Amount. v4.6 treats it as an ordinary
non-zero gesture update; v4.7 can detect it and apply the additional long-line layer.

The graph shapes existing v4.5 anchors rather than inventing new acoustic dimensions.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field
import math
from score_expression_graph_v40 import PPQ

SENTINEL_NORM=1.0/127.0

@dataclass
class PhraseArcV47:
    phrase_id:int
    part:int
    lane_channel:int
    source_ids:list[str]
    start_tick:int
    end_tick:int
    note_count:int
    duration_beats:float
    contour:str
    apex_u:float
    energy_start:float
    energy_apex:float
    energy_end:float
    vibrato_rate_start_hz:float
    vibrato_rate_apex_hz:float
    vibrato_rate_end_hz:float
    bow_reserve_end:float
    warnings:list[str]=field(default_factory=list)

def _clamp(x,a=0.0,b=1.0):return max(a,min(b,float(x)))
def _smooth(x):
    x=_clamp(x);return x*x*(3-2*x)

def _chains(g):
    lanes={}
    for n in g.notes:lanes.setdefault((n.part,n.lane_channel),[]).append(n)
    out=[]
    for key,notes in sorted(lanes.items()):
        notes.sort(key=lambda n:(n.start_tick,n.pitch))
        cur=[]
        for n in notes:
            if not cur:
                cur=[n]
            elif cur[-1].transition_out_link_id and n.transition_in_link_id==cur[-1].transition_out_link_id:
                cur.append(n)
            else:
                if len(cur)>=2:out.append((key,cur))
                cur=[n]
        if len(cur)>=2:out.append((key,cur))
    return out

def _contour(notes):
    pitches=[n.pitch for n in notes]
    if len(pitches)<3:
        return "rising" if pitches[-1]>pitches[0] else ("falling" if pitches[-1]<pitches[0] else "arch")
    hi=max(range(len(pitches)),key=lambda i:pitches[i])
    lo=min(range(len(pitches)),key=lambda i:pitches[i])
    if hi not in (0,len(pitches)-1):return "arch"
    if lo not in (0,len(pitches)-1):return "valley"
    if pitches[-1]>=pitches[0]+3:return "rising"
    if pitches[-1]<=pitches[0]-3:return "falling"
    return "sustained"

def _arc_value(contour,u,apex=.62):
    u=_clamp(u)
    if contour=="rising": return .90+.16*_smooth(u)
    if contour=="falling":return 1.06-.18*_smooth(u)
    if contour=="valley": return 1.03-.15*math.sin(math.pi*u)
    if contour=="sustained":return .96+.08*math.sin(math.pi*u)
    # arch
    if u<=apex:return .90+.18*_smooth(u/max(.001,apex))
    return 1.08-.20*_smooth((u-apex)/max(.001,1-apex))

def plan_phrase_longlines_v47(g):
    arcs=[];pid=0
    for (part,lane),notes in _chains(g):
        pid+=1
        start=notes[0].start_tick;end=notes[-1].end_tick;span=max(1,end-start)
        contour=_contour(notes)
        apex=.62 if contour=="arch" else (.72 if contour=="rising" else .48)
        # Phrase-level bow reserve is an abstract 1->0 budget, reset by authored/solver bow changes.
        reserve=1.0
        for ni,n in enumerate(notes):
            n.phrase_longline_id=pid
            n.phrase_longline_contour=contour
            n.phrase_longline_apex_u=apex
            n.phrase_longline_enabled=True
            n.phrase_longline_flags.append("phrase_energy_arc")
            dur=max(1,n.end_tick-n.start_tick)
            for a in n.gesture_anchors:
                tick=n.start_tick+float(a["u"])*dur
                u=_clamp((tick-start)/span)
                arc=_arc_value(contour,u,apex)
                # Existing anchor dimensions are shaped conservatively.
                a["dynamics_energy"]=round(_clamp(float(a["dynamics_energy"])*arc),6)
                a["bow_pressure"]=round(_clamp(float(a["bow_pressure"])*(0.94+0.10*(arc-0.9)/0.18)),6)
                a["contact_point"]=round(_clamp(float(a["contact_point"])+(arc-1.0)*.055),6)
                # Phrase vibrato grows toward long-line intensity but never forces vibrato onto straight notes.
                if float(a["vibrato_depth"])>.02:
                    a["vibrato_depth"]=round(_clamp(float(a["vibrato_depth"])*(0.92+0.16*_smooth(u))),6)
                a["phrase_u"]=round(u,6)
                a["phrase_energy"]=round(_clamp(arc/1.08),6)
            consumption=((n.end_tick-n.start_tick)/float(PPQ))*(.11+.16*float(n.bow_pressure))
            if n.bow_change:reserve=1.0
            reserve=max(0.0,reserve-consumption)
            n.phrase_bow_reserve=reserve
            n.phrase_dynamic_momentum=_clamp((_arc_value(contour,(n.start_tick-start)/span,apex)-.9)/.18)
            n.phrase_vibrato_rate_hz=4.7+1.0*n.phrase_dynamic_momentum
            n.phrase_longline_flags.append("vibrato_rate_target")
            if reserve<.12:n.phrase_longline_flags.append("low_bow_reserve")

        duration_beats=(end-start)/float(PPQ)
        warnings=[]
        if duration_beats>12 and not any(n.bow_change for n in notes[1:]):
            warnings.append("very_long_phrase_without_internal_bow_change")
        arcs.append(PhraseArcV47(
            pid,part,lane,[n.source_id for n in notes],start,end,len(notes),duration_beats,
            contour,apex,
            _arc_value(contour,0,apex),_arc_value(contour,apex,apex),_arc_value(contour,1,apex),
            4.7,5.7,5.0,reserve,warnings
        ))
    return g,arcs

def phrase_graph_dict(arcs):
    return {"schema":1,"version":"4.7","sentinel_cc38_norm":SENTINEL_NORM,
            "phrase_count":len(arcs),"phrases":[asdict(x) for x in arcs]}
