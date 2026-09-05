"""SONICRAFT v5.4 Conductor-Steered Candidate Generation.

Moves long-form intent upstream: A/B/C are no longer globally identical repair personalities.
They remain Conservative/Balanced/Expressive, but their control envelopes are gently steered by
the current macro Section Character before any Shadow Render occurs.

Hard boundaries:
- D Original is never modified.
- Note pitch/start/end/voice/staff/lane/articulation identity are not changed.
- No acoustic model, new CC, or ParamID is introduced.
- Steering uses only existing Dynamics/Vibrato/Bow/Transition/Ensemble control metadata.
- Every target is bounded by D-derived Conductor Intent.
- Candidate pruning is progressive: deferred candidates are rendered if the initial Audio Judge
  margin is insufficient.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass,asdict,field
from statistics import mean
from string_performance_critic_v48 import evaluate_performance_v48

IMMUTABLE=("part","start_tick","end_tick","pitch","velocity","voice","staff","source_id",
           "lane_channel","base_art","stack")

# Per-character candidate target offsets around the D-derived section target.
# Values are deliberately small. These are candidate search directions, not a new interpretation.
PROFILES={
 "intro":{
   "A":{"dyn":-.035,"vib":-.030,"rate":-.14,"bow":-.030,"transition":-.035,"desk":.88,"blend":.34},
   "B":{"dyn":-.010,"vib":-.010,"rate":-.05,"bow":-.010,"transition":-.010,"desk":.94,"blend":.28},
   "C":{"dyn":+.015,"vib":+.015,"rate":+.05,"bow":+.010,"transition":+.010,"desk":1.00,"blend":.22},
 },
 "build":{
   "A":{"dyn":-.018,"vib":-.018,"rate":-.08,"bow":-.015,"transition":-.010,"desk":.94,"blend":.26},
   "B":{"dyn":+.018,"vib":+.015,"rate":+.07,"bow":+.012,"transition":+.018,"desk":.98,"blend":.30},
   "C":{"dyn":+.052,"vib":+.045,"rate":+.20,"bow":+.035,"transition":+.030,"desk":1.02,"blend":.34},
 },
 "sustain":{
   "A":{"dyn":-.018,"vib":-.020,"rate":-.08,"bow":-.016,"transition":-.012,"desk":.92,"blend":.28},
   "B":{"dyn":+.002,"vib":+.002,"rate":+.01,"bow":+.002,"transition":+.008,"desk":.96,"blend":.30},
   "C":{"dyn":+.028,"vib":+.032,"rate":+.13,"bow":+.018,"transition":+.018,"desk":1.00,"blend":.30},
 },
 "climax":{
   "A":{"dyn":+.005,"vib":+.002,"rate":+.02,"bow":+.002,"transition":+.005,"desk":.94,"blend":.22},
   "B":{"dyn":+.038,"vib":+.038,"rate":+.17,"bow":+.028,"transition":+.030,"desk":.98,"blend":.32},
   "C":{"dyn":+.070,"vib":+.062,"rate":+.28,"bow":+.050,"transition":+.045,"desk":1.02,"blend":.36},
 },
 "release":{
   "A":{"dyn":-.040,"vib":-.038,"rate":-.18,"bow":-.032,"transition":-.022,"desk":.86,"blend":.34},
   "B":{"dyn":-.018,"vib":-.020,"rate":-.09,"bow":-.016,"transition":-.010,"desk":.90,"blend":.30},
   "C":{"dyn":+.005,"vib":+.005,"rate":+.02,"bow":+.004,"transition":+.004,"desk":.96,"blend":.22},
 },
 "resolution":{
   "A":{"dyn":-.045,"vib":-.045,"rate":-.20,"bow":-.036,"transition":-.028,"desk":.84,"blend":.36},
   "B":{"dyn":-.020,"vib":-.025,"rate":-.11,"bow":-.018,"transition":-.014,"desk":.88,"blend":.32},
   "C":{"dyn":+.002,"vib":+.002,"rate":+.01,"bow":+.002,"transition":+.002,"desk":.94,"blend":.20},
 },
}

PRIMARY_SLOTS={
    "intro":("A","B","D"),
    "build":("A","B","C","D"),
    "sustain":("A","B","C","D"),
    "climax":("B","C","D"),
    "release":("A","B","D"),
    "resolution":("A","B","D"),
}
ALL_SLOTS=("A","B","C","D")

@dataclass
class SteeringSectionReportV54:
    section_id:int
    character:str
    slot:str
    notes:int
    anchors:int
    ceiling_clamps:int
    dynamic_before:float
    dynamic_after:float
    vibrato_before:float
    vibrato_after:float
    bow_before:float
    bow_after:float
    critic_before:float
    critic_after:float

@dataclass
class CandidateSteeringReportV54:
    intent_hash:str
    sections:list[SteeringSectionReportV54]=field(default_factory=list)
    active_slot_policy:dict=field(default_factory=dict)
    def as_dict(self):
        return {
            "schema":1,"version":"5.4","intent_hash":self.intent_hash,
            "active_slot_policy":self.active_slot_policy,
            "sections":[asdict(x) for x in self.sections],
        }

def _clamp(x,a=0.0,b=1.0):return max(a,min(b,float(x)))

def section_for_tick_v54(intent,tick):
    tick=int(tick)
    for s in intent.sections:
        if int(s.start_tick)<=tick<int(s.end_tick):return s
    return intent.sections[-1]

def render_slots_for_window_v54(intent,start_tick,end_tick):
    mid=(int(start_tick)+int(end_tick))//2
    s=section_for_tick_v54(intent,mid)
    active=list(PRIMARY_SLOTS.get(s.character,ALL_SLOTS))
    deferred=[x for x in ALL_SLOTS if x not in active]
    return {
        "section_id":int(s.section_id),"character":str(s.character),
        "active":active,"deferred":deferred,
        "progressive":bool(deferred),
    }

def _target(section,profile,key):
    if key=="dyn":
        return min(float(section.dynamic_ceiling),_clamp(float(section.dynamic_mean)+float(profile["dyn"])))
    if key=="vib":
        return _clamp(float(section.vibrato_depth)+float(profile["vib"]))
    if key=="rate":
        return max(3.8,min(7.0,float(section.vibrato_rate_hz)+float(profile["rate"])))
    if key=="bow":
        return _clamp(float(section.bow_pressure)+float(profile["bow"]))
    raise KeyError(key)

def _blend(old,target,amount):
    return old*(1.0-amount)+target*amount

def _section_notes(g,section):
    return [n for n in g.notes if int(n.start_tick)<int(section.end_tick) and int(n.end_tick)>int(section.start_tick)]

def _anchor_mean(notes,key,fallback):
    vals=[]
    for n in notes:
        for a in getattr(n,"gesture_anchors",[]) or []:
            vals.append(float(a.get(key,fallback(n))))
    return mean(vals) if vals else 0.0

def _recompute_phrase_reserve(g):
    by={}
    for n in g.notes:
        pid=int(getattr(n,"phrase_longline_id",0) or 0)
        if pid:by.setdefault((int(n.part),int(n.lane_channel),pid),[]).append(n)
    for notes in by.values():
        notes.sort(key=lambda n:(int(n.start_tick),int(n.pitch)))
        reserve=1.0
        for n in notes:
            if bool(getattr(n,"bow_change",False)):reserve=1.0
            beats=max(0.0,(int(n.end_tick)-int(n.start_tick))/960.0)
            reserve=max(0.0,reserve-beats*(.11+.16*float(n.bow_pressure)))
            n.phrase_bow_reserve=reserve

def _immutability_signature(g):
    return [(getattr(n,k) for k in IMMUTABLE) for n in g.notes]

def _immutable_tuple(n):
    return tuple(getattr(n,k) for k in IMMUTABLE)

def steer_candidate_v54(base,candidate,slot,intent):
    if slot=="D":return deepcopy(base),[]
    if slot not in "ABC":raise ValueError(slot)
    cg=deepcopy(candidate)
    base_sig=[_immutable_tuple(n) for n in base.notes]
    before_score,_=evaluate_performance_v48(cg)
    reports=[]

    for section in intent.sections:
        notes=_section_notes(cg,section)
        if not notes:continue
        p=PROFILES.get(section.character,PROFILES["sustain"])[slot]
        anchors=sum(len(getattr(n,"gesture_anchors",[]) or []) for n in notes)
        dyn_before=_anchor_mean(notes,"dynamics_energy",lambda n:float(n.cc1)/127.0)
        vib_before=_anchor_mean(notes,"vibrato_depth",lambda n:float(n.cc3)/127.0)
        bow_before=mean(float(n.bow_pressure) for n in notes)

        dt=_target(section,p,"dyn");vt=_target(section,p,"vib")
        rt=_target(section,p,"rate");bt=_target(section,p,"bow")
        blend=float(p["blend"]);clamps=0

        for n in notes:
            # Existing v4.8 repair remains primary; steering only nudges it toward section intent.
            n.bow_pressure=_clamp(_blend(float(n.bow_pressure),bt,blend))
            if float(getattr(n,"phrase_vibrato_rate_hz",0.0))>0:
                n.phrase_vibrato_rate_hz=max(3.8,min(7.0,_blend(float(n.phrase_vibrato_rate_hz),rt,blend)))

            # Transition treatment follows section character, but physical topology is untouched.
            if int(getattr(n,"transition_in_link_id",0) or 0)>0:
                n.transition_continuity=_clamp(float(n.transition_continuity)+float(p["transition"])*blend)
                n.transition_duration_ms=max(12.0,min(180.0,float(n.transition_duration_ms)*(1.0+float(p["transition"])*.55)))

            # Desk looseness scales existing deterministic offset rather than inventing timing.
            n.ensemble_attack_offset_ms=float(n.ensemble_attack_offset_ms)*float(p["desk"])

            for a in getattr(n,"gesture_anchors",[]) or []:
                old=float(a.get("dynamics_energy",float(n.cc1)/127.0))
                nv=_clamp(_blend(old,dt,blend))
                if nv>float(section.dynamic_ceiling):
                    nv=float(section.dynamic_ceiling);clamps+=1
                a["dynamics_energy"]=round(nv,6)

                oldv=float(a.get("vibrato_depth",float(n.cc3)/127.0))
                # Never force vibrato onto an intentionally straight anchor.
                if oldv>.02:
                    a["vibrato_depth"]=round(_clamp(_blend(oldv,vt,blend)),6)

                oldp=float(a.get("bow_pressure",float(n.bow_pressure)))
                a["bow_pressure"]=round(_clamp(_blend(oldp,bt,blend)),6)

        dyn_after=_anchor_mean(notes,"dynamics_energy",lambda n:float(n.cc1)/127.0)
        vib_after=_anchor_mean(notes,"vibrato_depth",lambda n:float(n.cc3)/127.0)
        bow_after=mean(float(n.bow_pressure) for n in notes)
        # Final critic is filled after all sections so each row gets a common global post score.
        reports.append([section,anchors,clamps,dyn_before,dyn_after,vib_before,vib_after,bow_before,bow_after])

    _recompute_phrase_reserve(cg)

    # Hard immutability assertion: steering cannot change musical note identity/timing/articulation.
    assert [_immutable_tuple(n) for n in cg.notes]==base_sig,"v5.4 steering changed immutable note identity"

    after_score,_=evaluate_performance_v48(cg)
    out=[]
    for section,anchors,clamps,db,da,vb,va,bb,ba in reports:
        out.append(SteeringSectionReportV54(
            int(section.section_id),str(section.character),slot,
            len(_section_notes(cg,section)),int(anchors),int(clamps),
            round(db,6),round(da,6),round(vb,6),round(va,6),round(bb,6),round(ba,6),
            float(before_score.overall),float(after_score.overall)
        ))
    return cg,out

def steer_candidates_v54(base,candidates,intent):
    out={};rows=[]
    for slot in "ABC":
        out[slot],rr=steer_candidate_v54(base,candidates[slot],slot,intent)
        rows.extend(rr)
    report=CandidateSteeringReportV54(
        intent_hash=str(intent.intent_hash),
        sections=rows,
        active_slot_policy={k:{"primary":list(v),"deferred":[s for s in ALL_SLOTS if s not in v]}
                            for k,v in PRIMARY_SLOTS.items()}
    )
    return out,report
