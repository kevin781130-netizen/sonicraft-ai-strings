"""SONICRAFT v4.6 Continuous Transition & Legato Path Graph.

Connects v4.5 note-internal gesture graphs into phrase-level trajectories.

The graph only links notes when the score/physical plan already indicates a connected bowed
transition. It never invents a slur. Linked boundaries reconcile dynamics, vibrato depth,
bow pressure/contact and portamento intent so the HQ renderer can interpolate through the
boundary instead of restarting every note.

Actual semitone pitch travel is executed in `string_transition_runtime_v46.py` from the written
note pitches plus the linked phrase window; score pitches remain unchanged.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field
import hashlib,math
from score_expression_graph_v40 import PPQ

MAX_LINK_GAP_TICKS=max(40,PPQ//48)

@dataclass
class TransitionLinkV46:
    link_id:int
    part:int
    lane_channel:int
    from_source_id:str
    to_source_id:str
    from_tick:int
    to_tick:int
    interval_semitones:int
    shift_semitones:int
    string_crossing:int
    mode:str
    duration_ms:float
    same_bow:bool
    explicit_portamento:bool
    continuity:float
    warnings:list[str]=field(default_factory=list)

def _clamp(x,a=0.0,b=1.0):return max(a,min(b,float(x)))
def _is_bowed(n):return n.base_art!=8
def _written_connected(a,b):
    gap=b.start_tick-a.end_tick
    if gap>MAX_LINK_GAP_TICKS:return False
    if not (_is_bowed(a) and _is_bowed(b)):return False
    return bool(
        a.slur or b.slur or (a.stack&2) or (b.stack&2) or
        a.base_art in (1,2) or b.base_art in (1,2) or
        b.portamento_route>.20
    )
def _mode(a,b):
    porta=bool(b.base_art==2 or b.portamento_route>.45)
    same_string=a.string_index==b.string_index
    same_bow=not bool(b.bow_change)
    if porta and same_string:return "same-string-portamento"
    if porta:return "cross-string-portamento"
    if same_bow and same_string:return "same-bow-legato-shift"
    if same_bow:return "same-bow-string-crossing"
    if same_string:return "rebow-legato-shift"
    return "rebow-string-crossing"

def _duration_ms(a,b):
    interval=abs(int(b.pitch)-int(a.pitch))
    shift=abs(int(b.shift_semitones))
    porta=bool(b.base_art==2 or b.portamento_route>.45)
    if porta:
        return max(35.0,min(190.0,42.0+interval*7.5+shift*2.0))
    return max(14.0,min(78.0,18.0+interval*3.0+shift*1.3))

def _anchor_blend(a,b,same_bow,porta):
    if not a.gesture_anchors or not b.gesture_anchors:return
    pa=a.gesture_anchors[-1];nb=b.gesture_anchors[0]
    # Dynamics continuity should not jump merely because a new MIDI note begins.
    energy=(float(pa["dynamics_energy"])+float(nb["dynamics_energy"]))*0.5
    vib=(float(pa["vibrato_depth"])+float(nb["vibrato_depth"]))*0.5

    if same_bow:
        pressure=(float(pa["bow_pressure"])+float(nb["bow_pressure"]))*0.5
        contact=(float(pa["contact_point"])+float(nb["contact_point"]))*0.5
        speed=(float(pa["bow_speed"])+float(nb["bow_speed"]))*0.5
    else:
        # A re-bow is continuous musically but contains a real mechanical release/re-attack.
        pressure=max(.12,min(.46,(float(pa["bow_pressure"])+float(nb["bow_pressure"]))*0.32))
        contact=(float(pa["contact_point"])+float(nb["contact_point"]))*0.5
        speed=max(.18,min(.52,(float(pa["bow_speed"])+float(nb["bow_speed"]))*0.42))

    pa["dynamics_energy"]=nb["dynamics_energy"]=round(_clamp(energy),6)
    pa["vibrato_depth"]=nb["vibrato_depth"]=round(_clamp(vib),6)
    pa["bow_pressure"]=nb["bow_pressure"]=round(_clamp(pressure),6)
    pa["contact_point"]=nb["contact_point"]=round(_clamp(contact),6)
    pa["bow_speed"]=nb["bow_speed"]=round(_clamp(speed),6)

    # At a linked boundary micro drift must converge instead of jumping to unrelated random phase.
    micro=(float(pa["micro_pitch_cents"])+float(nb["micro_pitch_cents"]))*0.25
    pa["micro_pitch_cents"]=nb["micro_pitch_cents"]=round(max(-5.0,min(5.0,micro)),6)
    if porta:
        pa["portamento"]=round(max(float(pa["portamento"]),.62),6)
        nb["portamento"]=round(max(float(nb["portamento"]),.62),6)

def build_continuous_transition_graph_v46(g):
    links=[];link_id=0
    lanes={}
    for n in g.notes:lanes.setdefault((n.part,n.lane_channel),[]).append(n)

    for (part,lane),notes in lanes.items():
        notes.sort(key=lambda n:(n.start_tick,n.pitch))
        for a,b in zip(notes,notes[1:]):
            if not _written_connected(a,b):continue
            link_id+=1
            mode=_mode(a,b)
            same_bow=not bool(b.bow_change)
            porta=bool(b.base_art==2 or b.portamento_route>.45)
            interval=int(b.pitch)-int(a.pitch)
            crossing=abs(int(b.string_index)-int(a.string_index))
            shift=abs(int(b.finger_semitone)-int(a.finger_semitone))
            duration=_duration_ms(a,b)
            continuity=.86
            if not same_bow:continuity-=.18
            if crossing:continuity-=min(.20,crossing*.07)
            if abs(interval)>=12:continuity-=.08
            continuity=_clamp(continuity)

            warnings=[]
            if crossing>=2 and same_bow:warnings.append("wide_same_bow_string_crossing")
            if a.ensemble_phrase_id and b.ensemble_phrase_id and a.ensemble_phrase_id!=b.ensemble_phrase_id:
                warnings.append("ensemble_phrase_boundary_link")

            _anchor_blend(a,b,same_bow,porta)

            a.transition_out_link_id=link_id
            b.transition_in_link_id=link_id
            a.transition_out_mode=mode
            b.transition_in_mode=mode
            a.transition_continuity=continuity
            b.transition_continuity=continuity
            a.transition_duration_ms=duration
            b.transition_duration_ms=duration
            a.transition_interval_semitones=interval
            b.transition_interval_semitones=interval
            a.transition_phrase_continuous=True
            b.transition_phrase_continuous=True
            a.transition_flags.append("continuous_transition_out")
            b.transition_flags.append("continuous_transition_in")
            if same_bow:
                a.transition_flags.append("bow_continuity")
                b.transition_flags.append("bow_continuity")
            if porta:
                a.transition_flags.append("portamento_path")
                b.transition_flags.append("portamento_path")

            links.append(TransitionLinkV46(
                link_id,part,lane,a.source_id,b.source_id,a.end_tick,b.start_tick,interval,shift,crossing,
                mode,duration,same_bow,porta,continuity,warnings
            ))
    return g,links

def transition_graph_dict(links):
    return {
        "schema":1,
        "version":"4.6",
        "link_count":len(links),
        "links":[asdict(x) for x in links],
    }
