"""SONICRAFT v4.8 Phrase Performance Critic & Auto-Repair.

Score-domain critic over the already-authored v4.1-v4.7 performance graph.
It does not listen to audio and therefore must not be confused with the v3.7 Audio Judge.

Dimensions:
- bow reserve / pressure sustainability
- transition risk vs continuity treatment
- vibrato rate/depth continuity
- long-line dynamics smoothness
- gesture spike control
- ensemble attack alignment

It generates three deliberately different deterministic repairs:
A Conservative  - minimal smoothing, preserve topology
B Balanced      - strongest structural cleanup; may introduce one safe re-bow split
C Expressive    - preserve larger musical arcs while fixing discontinuities

Original is slot D for the existing A/B/C/D Audio Judge workflow.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field
from copy import deepcopy
from statistics import mean,pstdev
import math

WEIGHTS={
    "bow_reserve":.20,
    "transition":.20,
    "vibrato":.15,
    "dynamics_arc":.15,
    "gesture_spikes":.15,
    "ensemble_alignment":.15,
}

@dataclass
class CriticIssueV48:
    severity:str
    dimension:str
    source_ids:list[str]=field(default_factory=list)
    detail:str=""

@dataclass
class CriticScoreV48:
    overall:float
    dimensions:dict[str,float]
    issue_count:int
    severe_count:int

@dataclass
class RepairCandidateV48:
    slot:str
    strategy:str
    description:str
    score_before:float
    score_after:float
    improvement:float
    edits:list[dict]=field(default_factory=list)

def _clamp(x,a=0.0,b=1.0):return max(a,min(b,float(x)))
def _score(penalty):return round(max(0.0,min(100.0,100.0-float(penalty))),3)

def _phrases(g):
    by={}
    for n in g.notes:
        pid=int(getattr(n,"phrase_longline_id",0) or 0)
        if pid:by.setdefault(pid,[]).append(n)
    for notes in by.values():notes.sort(key=lambda n:(n.start_tick,n.pitch))
    return by

def _anchor_series(notes,key):
    out=[]
    for n in notes:
        for a in getattr(n,"gesture_anchors",[]) or []:
            out.append((n.source_id,float(a.get("phrase_u",a.get("u",0.0))),float(a.get(key,0.0))))
    return out

def _jump_penalty(vals,threshold,scale):
    if len(vals)<2:return 0.0
    return sum(max(0.0,abs(b-a)-threshold)*scale for a,b in zip(vals,vals[1:]))

def evaluate_performance_v48(g):
    issues=[]
    phrases=_phrases(g)

    # 1. Bow reserve / pressure sustainability.
    bow_pen=0.0
    low=[]
    for n in g.notes:
        reserve=float(getattr(n,"phrase_bow_reserve",1.0))
        if reserve<.18:
            p=(.18-reserve)*170.0
            bow_pen+=p
            low.append(n.source_id)
    if low:
        issues.append(CriticIssueV48("warning" if min(float(getattr(n,"phrase_bow_reserve",1)) for n in g.notes)>=.07 else "error",
                                     "bow_reserve",low[:16],f"{len(low)} notes enter low phrase bow reserve"))
    bow_score=_score(min(100,bow_pen/max(1,len(g.notes))*2.6))

    # 2. Transition physical risk vs amount of continuity treatment.
    trans_pen=0.0;trans_bad=[]
    for n in g.notes:
        if not getattr(n,"transition_in_link_id",0):continue
        risk=float(getattr(n,"transition_risk",0.0))
        continuity=float(getattr(n,"transition_continuity",0.0))
        duration=float(getattr(n,"transition_duration_ms",0.0))
        untreated=max(0.0,risk-.42)*(1.0-.55*continuity)
        if risk>.62 and duration<45:untreated+=.12
        trans_pen+=untreated*120
        if untreated>.16:trans_bad.append(n.source_id)
    if trans_bad:issues.append(CriticIssueV48("warning","transition",trans_bad[:16],"high-risk links are insufficiently cushioned by transition continuity"))
    trans_score=_score(min(100,trans_pen/max(1,sum(bool(getattr(n,"transition_in_link_id",0)) for n in g.notes))))

    # 3. Vibrato continuity: rate per note + depth at linked boundaries.
    vib_pen=0.0;vib_bad=[]
    for pid,notes in phrases.items():
        rates=[float(getattr(n,"phrase_vibrato_rate_hz",0.0)) for n in notes if float(getattr(n,"phrase_vibrato_rate_hz",0.0))>0]
        vib_pen+=_jump_penalty(rates,.34,26)
        for a,b in zip(notes,notes[1:]):
            if not (a.gesture_anchors and b.gesture_anchors):continue
            da=float(a.gesture_anchors[-1].get("vibrato_depth",0))
            db=float(b.gesture_anchors[0].get("vibrato_depth",0))
            jump=abs(db-da)
            if jump>.16:
                vib_pen+=(jump-.16)*90;vib_bad.extend([a.source_id,b.source_id])
    if vib_bad:issues.append(CriticIssueV48("warning","vibrato",list(dict.fromkeys(vib_bad))[:16],"vibrato depth/rate discontinuity at linked boundaries"))
    vib_score=_score(min(100,vib_pen/max(1,len(phrases))))

    # 4. Dynamics long-line smoothness: derivative spikes in phrase-energy anchors.
    dyn_pen=0.0;dyn_bad=[]
    for pid,notes in phrases.items():
        vals=[x[2] for x in _anchor_series(notes,"dynamics_energy")]
        if len(vals)<3:continue
        dif=[b-a for a,b in zip(vals,vals[1:])]
        for i,(a,b) in enumerate(zip(dif,dif[1:])):
            jerk=abs(b-a)
            if jerk>.18:
                dyn_pen+=(jerk-.18)*130
                dyn_bad.extend([notes[min(len(notes)-1,i//5)].source_id])
    if dyn_bad:issues.append(CriticIssueV48("warning","dynamics_arc",list(dict.fromkeys(dyn_bad))[:16],"long-line dynamics contains local acceleration spikes"))
    dyn_score=_score(min(100,dyn_pen/max(1,len(phrases))))

    # 5. Gesture spike control across pressure/contact/micro-pitch and bow speed.
    gesture_pen=0.0;gesture_bad=[]
    spec=(("bow_pressure",.18,90),("contact_point",.14,100),("bow_speed",.22,75),("micro_pitch_cents",7.5,4.5))
    for pid,notes in phrases.items():
        for key,thr,scale in spec:
            vals=[x[2] for x in _anchor_series(notes,key)]
            p=_jump_penalty(vals,thr,scale)
            if p>8:gesture_bad.extend(n.source_id for n in notes[:3])
            gesture_pen+=p
    if gesture_bad:issues.append(CriticIssueV48("warning","gesture_spikes",list(dict.fromkeys(gesture_bad))[:16],"pressure/contact/bow-speed/micro-pitch contains abrupt phrase-local jumps"))
    gesture_score=_score(min(100,gesture_pen/max(1,len(phrases))))

    # 6. Ensemble alignment: excessive spread and coordination-risk outliers.
    ens_pen=0.0;ens_bad=[]
    starts={}
    for n in g.notes:
        starts.setdefault(int(n.start_tick),[]).append(n)
        r=float(getattr(n,"ensemble_coordination_risk",0.0))
        if r>.22:ens_pen+=(r-.22)*120;ens_bad.append(n.source_id)
    for tick,notes in starts.items():
        parts={n.part for n in notes}
        if len(parts)<2:continue
        offs=[float(getattr(n,"ensemble_attack_offset_ms",0.0)) for n in notes]
        spread=max(offs)-min(offs)
        if spread>5.0:
            ens_pen+=(spread-5.0)*5.0
            ens_bad.extend(n.source_id for n in notes)
    if ens_bad:issues.append(CriticIssueV48("info","ensemble_alignment",list(dict.fromkeys(ens_bad))[:16],"ensemble attack spread/risk exceeds critic comfort zone"))
    ens_score=_score(min(100,ens_pen/max(1,len(starts))*2.0))

    dims={
        "bow_reserve":bow_score,
        "transition":trans_score,
        "vibrato":vib_score,
        "dynamics_arc":dyn_score,
        "gesture_spikes":gesture_score,
        "ensemble_alignment":ens_score,
    }
    overall=round(sum(dims[k]*WEIGHTS[k] for k in WEIGHTS),3)
    severe=sum(1 for x in issues if x.severity=="error")
    return CriticScoreV48(overall,dims,len(issues),severe),issues

def _smooth_values(vals,blend,limit=None):
    if len(vals)<3:return list(vals)
    src=list(vals);out=list(vals)
    for i in range(1,len(vals)-1):
        target=(src[i-1]+2*src[i]+src[i+1])/4.0
        out[i]=src[i]*(1-blend)+target*blend
    if limit is not None:
        for i in range(1,len(out)):
            d=out[i]-out[i-1]
            if abs(d)>limit:out[i]=out[i-1]+math.copysign(limit,d)
    return out

def _apply_anchor_smoothing(notes,blend,expressive=False):
    edits=[]
    keys_limits={
        "dynamics_energy":.18 if expressive else .14,
        "bow_pressure":.14,
        "contact_point":.11,
        "bow_speed":.18,
        "vibrato_depth":.13,
        "micro_pitch_cents":6.0,
    }
    flat=[]
    for n in notes:
        for ai,a in enumerate(n.gesture_anchors or []):flat.append((n,ai,a))
    if len(flat)<3:return edits
    for key,limit in keys_limits.items():
        vals=[float(a.get(key,0.0)) for _,_,a in flat]
        sm=_smooth_values(vals,blend,limit)
        for (n,ai,a),old,new in zip(flat,vals,sm):
            if abs(new-old)>1e-6:
                if key=="micro_pitch_cents":a[key]=round(max(-14.0,min(14.0,new)),6)
                else:a[key]=round(_clamp(new),6)
    edits.append({"kind":"gesture_smoothing","source_ids":[n.source_id for n in notes],
                  "blend":blend,"expressive":expressive})
    return edits

def _recompute_reserve(notes,pressure_scale=1.0):
    reserve=1.0
    for n in notes:
        if n.bow_change:reserve=1.0
        n.bow_pressure=_clamp(float(n.bow_pressure)*pressure_scale)
        beats=max(0.0,(n.end_tick-n.start_tick)/960.0)
        reserve=max(0.0,reserve-beats*(.11+.16*float(n.bow_pressure)))
        n.phrase_bow_reserve=reserve

def _safe_rebow_split(notes):
    if len(notes)<4:return None
    candidates=notes[1:-1]
    if not candidates:return None
    # Favor near-middle low-risk boundary, and do not override explicit bow marks.
    mid=(notes[0].start_tick+notes[-1].end_tick)/2
    cand=min(candidates,key=lambda n:(float(getattr(n,"transition_risk",0.0))*3+abs(n.start_tick-mid)/max(1,notes[-1].end_tick-notes[0].start_tick)))
    if "up-bow" in cand.technical or "down-bow" in cand.technical:return None
    return cand

def repair_candidate_v48(g,strategy,policy=None):
    cg=deepcopy(g);edits=[]
    cfg={
        "A":{"blend":.24,"pressure":.96,"attack_limit":4.5,"continuity":.05,"rebow":False,"expressive":False},
        "B":{"blend":.52,"pressure":.90,"attack_limit":3.2,"continuity":.14,"rebow":True,"expressive":False},
        "C":{"blend":.36,"pressure":.94,"attack_limit":5.0,"continuity":.09,"rebow":False,"expressive":True},
    }[strategy]
    if policy:
        # v4.9 policy is a bounded, explainable multiplier set. v4.8 behavior is exactly the policy=None path.
        smooth=max(.65,min(1.35,float(policy.get("smoothing",1.0))))
        bow_relief=max(.65,min(1.35,float(policy.get("bow_relief",1.0))))
        transition_gain=max(.65,min(1.35,float(policy.get("transition",1.0))))
        ensemble=max(.65,min(1.35,float(policy.get("ensemble_tightness",1.0))))
        expressive=max(.65,min(1.35,float(policy.get("expressive_apex",1.0))))
        cfg["blend"]=max(.08,min(.72,cfg["blend"]*smooth))
        cfg["pressure"]=max(.72,min(1.0,1.0-(1.0-cfg["pressure"])*bow_relief))
        cfg["continuity"]=max(.02,min(.24,cfg["continuity"]*transition_gain))
        cfg["attack_limit"]=max(2.4,min(6.5,cfg["attack_limit"]/ensemble))
        cfg["expressive_gain"]=expressive
    else:
        cfg["expressive_gain"]=1.0
    phrases=_phrases(cg)
    for pid,notes in phrases.items():
        edits+=_apply_anchor_smoothing(notes,cfg["blend"],cfg["expressive"])
        min_res=min(float(getattr(n,"phrase_bow_reserve",1.0)) for n in notes)
        scale=cfg["pressure"] if min_res<.24 else 1.0
        if scale<1:
            _recompute_reserve(notes,scale)
            edits.append({"kind":"bow_pressure_relief","phrase_id":pid,"scale":scale})
        if cfg["rebow"] and min(float(getattr(n,"phrase_bow_reserve",1.0)) for n in notes)<.12:
            cand=_safe_rebow_split(notes)
            if cand is not None:
                idx=notes.index(cand);prev=notes[idx-1]
                link=int(getattr(cand,"transition_in_link_id",0))
                cand.bow_change=True
                if link:
                    prev.transition_out_link_id=0;cand.transition_in_link_id=0
                    prev.transition_flags.append("critic_rebow_split")
                    cand.transition_flags.append("critic_rebow_split")
                _recompute_reserve(notes,1.0)
                edits.append({"kind":"safe_rebow_split","phrase_id":pid,"source_id":cand.source_id,"broken_link_id":link})

        # Smooth per-note vibrato-rate targets and improve treatment of high-risk links.
        rates=[float(getattr(n,"phrase_vibrato_rate_hz",0.0)) for n in notes]
        sr=_smooth_values(rates,cfg["blend"],.28)
        for n,r in zip(notes,sr):
            if r>0:n.phrase_vibrato_rate_hz=round(max(4.2,min(6.2,r)),6)
            if n.transition_in_link_id and n.transition_risk>.48:
                old=float(n.transition_continuity)
                n.transition_continuity=_clamp(old+cfg["continuity"])
                n.transition_duration_ms=max(float(n.transition_duration_ms),38.0+48.0*float(n.transition_risk))

    # Tighten ensemble spread without eliminating intended desk separation.
    starts={}
    for n in cg.notes:starts.setdefault(n.start_tick,[]).append(n)
    for tick,notes in starts.items():
        if len({n.part for n in notes})<2:continue
        offs=[float(n.ensemble_attack_offset_ms) for n in notes]
        center=sum(offs)/len(offs)
        for n in notes:
            old=float(n.ensemble_attack_offset_ms)
            new=center+max(-cfg["attack_limit"]/2,min(cfg["attack_limit"]/2,old-center))
            if abs(new-old)>.01:
                n.ensemble_attack_offset_ms=round(new,6)
        if max(offs)-min(offs)>cfg["attack_limit"]:
            edits.append({"kind":"ensemble_spread_clamp","tick":tick,"max_spread_ms":cfg["attack_limit"]})

    # Expressive candidate preserves a slightly broader dynamics apex after smoothing.
    if cfg["expressive"]:
        for notes in phrases.values():
            for n in notes:
                for a in n.gesture_anchors or []:
                    u=float(a.get("phrase_u",a.get("u",0.0)))
                    lift=.025*cfg["expressive_gain"]*math.sin(math.pi*_clamp(u))
                    a["dynamics_energy"]=round(_clamp(float(a.get("dynamics_energy",0.5))+lift),6)
                    if float(a.get("vibrato_depth",0.0))>.02:
                        a["vibrato_depth"]=round(_clamp(float(a["vibrato_depth"])+lift*.55),6)
        edits.append({"kind":"expressive_apex_preservation","amount":.025})

    before,_=evaluate_performance_v48(g)
    after,_=evaluate_performance_v48(cg)
    desc={
        "A":"Conservative: minimal smoothing, topology preserved, small bow-pressure relief.",
        "B":"Balanced: stronger smoothing/alignment repair; may split one safe re-bow when reserve is critical.",
        "C":"Expressive: repair discontinuities while preserving a broader long-line apex.",
    }[strategy]
    return cg,RepairCandidateV48(strategy,{"A":"Conservative","B":"Balanced","C":"Expressive"}[strategy],
                                 desc,before.overall,after.overall,round(after.overall-before.overall,3),edits)

def generate_repairs_v48(g,policy=None):
    score,issues=evaluate_performance_v48(g)
    candidates={}
    reports={}
    for slot in ("A","B","C"):
        cg,rep=repair_candidate_v48(g,slot,policy)
        candidates[slot]=cg;reports[slot]=rep
    # Structural recommendation only. Audio Judge remains final authority.
    best=max(reports.values(),key=lambda r:(r.score_after,r.improvement,{"B":2,"A":1,"C":0}[r.slot]))
    return score,issues,candidates,reports,best.slot

def critic_bundle_dict(score,issues,reports,recommended):
    return {
        "schema":1,"version":"4.8",
        "critic_scope":"score/performance controls only; NOT audio listening",
        "original_slot":"D",
        "weights":WEIGHTS,
        "original":{"overall":score.overall,"dimensions":score.dimensions,
                    "issue_count":score.issue_count,"severe_count":score.severe_count},
        "issues":[asdict(x) for x in issues],
        "candidates":{k:asdict(v) for k,v in reports.items()},
        "structural_recommendation":recommended,
        "final_authority":"render A/B/C/D and use existing Audio Judge for sonic winner",
    }
