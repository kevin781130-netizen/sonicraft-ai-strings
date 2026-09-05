"""SONICRAFT v5.3 Long-Form Conductor Intent / Section Character Lock.

Builds a deterministic macro-performance plan from D Original, then protects that plan while
v5.1/v5.2 optimize individual phrases.

This is not score composition and does not invent a new musical interpretation. It extracts a
long-form intent envelope from the authored score + existing SONICRAFT performance graph:
- macro section boundaries aligned to note/phrase onsets
- intended climax location
- dynamic ceiling / trajectory
- vibrato palette
- bow-energy character
- desk looseness
- transition density/treatment
- per-part lead/foundation role locks

Local Audio Judge still supplies sonic evidence. The Conductor Lock only chooses among candidates
that remain close enough to the local winner, and D Original is always a safety candidate.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field
from itertools import product
from statistics import mean,pstdev
import hashlib,json,math

from global_performance_coherence_v52 import (
    _allowed_slots,merge_graph_decisions_v52,evaluate_global_coherence_v52,
    PASS_SCORE as COHERENCE_PASS,MAX_EDGE_EXCESS as COHERENCE_EDGE
)

PPQ=960
MAX_SECTIONS=8
MIN_SECTION_BEATS=4.0
TARGET_SECTION_COUNT=6
INTENT_PASS_SCORE=84.0
MAX_SECTION_EXCESS=1.55
AUDIO_DROP_LIMIT=.075

DIM_WEIGHTS={
    "dynamic":.26,
    "vibrato":.18,
    "bow":.17,
    "desk":.10,
    "transition":.13,
    "role":.16,
}

@dataclass
class SectionIntentV53:
    section_id:int
    start_tick:int
    end_tick:int
    start_u:float
    end_u:float
    character:str
    dynamic_mean:float
    dynamic_peak:float
    dynamic_ceiling:float
    vibrato_depth:float
    vibrato_rate_hz:float
    bow_pressure:float
    bow_reserve_floor:float
    desk_looseness_ms:float
    transition_density:float
    transition_treatment:float
    part_roles:dict
    note_count:int

@dataclass
class ConductorIntentV53:
    schema:int
    version:str
    song_start_tick:int
    song_end_tick:int
    climax_section_id:int
    climax_u:float
    global_dynamic_ceiling:float
    vibrato_palette_center:float
    vibrato_palette_std:float
    vibrato_rate_center_hz:float
    desk_looseness_center_ms:float
    sections:list[SectionIntentV53]
    intent_hash:str=""
    def as_dict(self):
        d={
            "schema":self.schema,"version":self.version,
            "song_start_tick":self.song_start_tick,"song_end_tick":self.song_end_tick,
            "climax_section_id":self.climax_section_id,"climax_u":round(float(self.climax_u),6),
            "global_dynamic_ceiling":round(float(self.global_dynamic_ceiling),6),
            "vibrato_palette_center":round(float(self.vibrato_palette_center),6),
            "vibrato_palette_std":round(float(self.vibrato_palette_std),6),
            "vibrato_rate_center_hz":round(float(self.vibrato_rate_center_hz),6),
            "desk_looseness_center_ms":round(float(self.desk_looseness_center_ms),6),
            "sections":[asdict(x) for x in self.sections],
        }
        d["intent_hash"]=self.intent_hash or _intent_hash(d)
        return d

@dataclass
class SectionAdherenceV53:
    section_id:int
    character:str
    excess:dict
    weighted_excess:float
    hard_violations:list[str]=field(default_factory=list)

@dataclass
class ConductorIntentReportV53:
    passed:bool
    score:float
    max_section_excess:float
    intended_climax_section:int
    observed_climax_section:int
    long_line_reversals:int
    hard_violations:list[str]
    sections:list[SectionAdherenceV53]
    reason:str
    def as_dict(self):
        return {
            "schema":1,"version":"5.3","passed":self.passed,"score":round(float(self.score),6),
            "max_section_excess":round(float(self.max_section_excess),6),
            "intended_climax_section":self.intended_climax_section,
            "observed_climax_section":self.observed_climax_section,
            "long_line_reversals":self.long_line_reversals,
            "hard_violations":self.hard_violations,"reason":self.reason,
            "sections":[asdict(x) for x in self.sections],
        }

def _clamp(x,a=0.0,b=1.0):return max(a,min(b,float(x)))

def _intent_hash(d):
    q=dict(d);q.pop("intent_hash",None)
    raw=json.dumps(q,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]

def _anchor_values(n,key,fallback):
    vals=[float(a.get(key,fallback)) for a in (getattr(n,"gesture_anchors",[]) or []) if key in a]
    return vals or [float(fallback)]

def _note_overlap(n,a,b):
    return max(0,min(int(n.end_tick),int(b))-max(int(n.start_tick),int(a)))

def _nearest_onset(target,onsets,lo,hi):
    c=[x for x in onsets if lo<x<hi]
    if not c:return int(target)
    return min(c,key=lambda x:abs(int(x)-int(target)))

def _section_boundaries(g):
    notes=list(g.notes)
    start=min(int(n.start_tick) for n in notes);end=max(int(n.end_tick) for n in notes)
    span=max(1,end-start)
    target_count=max(2,min(MAX_SECTIONS,TARGET_SECTION_COUNT,
                           int(round(span/max(PPQ*MIN_SECTION_BEATS,1)))))
    target_len=span/float(target_count)
    onsets=sorted({int(n.start_tick) for n in notes})
    # Long-line phrase starts and ensemble phrase starts are especially useful macro anchors.
    phrase_starts=sorted({int(n.start_tick) for n in notes
                          if int(getattr(n,"phrase_longline_id",0) or 0)>0 and
                          not any(int(m.phrase_longline_id)==int(n.phrase_longline_id) and
                                  int(m.start_tick)<int(n.start_tick) for m in notes)})
    candidates=sorted(set(onsets)|set(phrase_starts)|{int(x["tick"]) for x in getattr(g,"time_signatures",[]) or []})
    out=[start]
    for i in range(1,target_count):
        target=start+target_len*i
        lo=out[-1]+int(PPQ*MIN_SECTION_BEATS*.65)
        hi=end-int(PPQ*MIN_SECTION_BEATS*.65)*(target_count-i-1)
        if hi<=lo:break
        use=_nearest_onset(target,candidates,lo,hi)
        use=max(lo,min(hi,int(use)))
        if use-out[-1]>=PPQ*2:out.append(use)
    if end>out[-1]:out.append(end)
    # Merge accidental very-short tail/head sections.
    changed=True
    while changed and len(out)>3:
        changed=False
        for i in range(len(out)-1):
            if out[i+1]-out[i]<int(PPQ*MIN_SECTION_BEATS*.55):
                if i+1<len(out)-1:del out[i+1]
                elif i>0:del out[i]
                changed=True;break
    return out

def _section_features(g,a,b):
    notes=[n for n in g.notes if _note_overlap(n,a,b)>0]
    if not notes:
        return {
            "dynamic_mean":0.0,"dynamic_peak":0.0,"vibrato_depth":0.0,"vibrato_rate_hz":0.0,
            "bow_pressure":0.0,"bow_reserve_floor":1.0,"desk_looseness_ms":0.0,
            "transition_density":0.0,"transition_treatment":0.0,"part_roles":{},"note_count":0
        }
    weights=[max(1,_note_overlap(n,a,b)) for n in notes]
    den=float(sum(weights))
    dyn=[];vib=[]
    for n,w in zip(notes,weights):
        dyn.extend((v,w/max(1,len(_anchor_values(n,"dynamics_energy",float(n.cc1)/127.0))))
                   for v in _anchor_values(n,"dynamics_energy",float(n.cc1)/127.0))
        vib.extend((v,w/max(1,len(_anchor_values(n,"vibrato_depth",float(n.cc3)/127.0))))
                   for v in _anchor_values(n,"vibrato_depth",float(n.cc3)/127.0))
    dyn_den=max(1e-9,sum(w for _,w in dyn));vib_den=max(1e-9,sum(w for _,w in vib))
    dynamic_mean=sum(v*w for v,w in dyn)/dyn_den
    vibrato_depth=sum(v*w for v,w in vib)/vib_den
    dynamic_peak=max(v for v,_ in dyn)
    rates=[float(n.phrase_vibrato_rate_hz) for n in notes if float(getattr(n,"phrase_vibrato_rate_hz",0.0))>0]
    bow_pressure=sum(float(n.bow_pressure)*w for n,w in zip(notes,weights))/den
    bow_reserve=min(float(getattr(n,"phrase_bow_reserve",1.0)) for n in notes)
    offs=[float(getattr(n,"ensemble_attack_offset_ms",0.0)) for n in notes]
    desk=pstdev(offs) if len(offs)>1 else (abs(offs[0]) if offs else 0.0)
    trans=[n for n in notes if int(getattr(n,"transition_in_link_id",0) or 0)>0]
    td=len(trans)/max(1,len(notes))
    tt=mean([_clamp(float(n.transition_continuity))*.65+
             _clamp(float(n.transition_duration_ms)/180.0)*.35 for n in trans]) if trans else 0.0

    part_roles={}
    for part in range(4):
        pn=[n for n in notes if int(n.part)==part]
        if not pn:continue
        cnt={"lead":0,"inner":0,"foundation":0}
        for n in pn:
            r=str(getattr(n,"ensemble_role","") or "inner")
            if r not in cnt:r="inner"
            cnt[r]+=1
        tot=max(1,len(pn))
        part_roles[str(part)]={k:cnt[k]/tot for k in cnt}

    return {
        "dynamic_mean":dynamic_mean,"dynamic_peak":dynamic_peak,
        "vibrato_depth":vibrato_depth,"vibrato_rate_hz":mean(rates) if rates else 0.0,
        "bow_pressure":bow_pressure,"bow_reserve_floor":bow_reserve,
        "desk_looseness_ms":desk,"transition_density":td,"transition_treatment":tt,
        "part_roles":part_roles,"note_count":len(notes),
    }

def _energy_metric(f):
    return .58*float(f["dynamic_mean"])+.18*float(f["dynamic_peak"])+.12*float(f["bow_pressure"])+.12*_clamp(float(f["vibrato_depth"]))

def _characterize(features,climax_idx):
    n=len(features);chars=[]
    dyn=[float(x["dynamic_mean"]) for x in features]
    for i,f in enumerate(features):
        if i==climax_idx:
            chars.append("climax");continue
        prev=dyn[i-1] if i>0 else dyn[i]
        nxt=dyn[i+1] if i+1<n else dyn[i]
        if i==0 and dyn[i]<=mean(dyn):
            chars.append("intro");continue
        if i==n-1:
            chars.append("resolution" if dyn[i]<max(dyn)-.04 else "sustain");continue
        if nxt-dyn[i]>=.035 or dyn[i]-prev>=.035:
            chars.append("build");continue
        if dyn[i]-nxt>=.035 or prev-dyn[i]>=.04:
            chars.append("release");continue
        chars.append("sustain")
    return chars

def build_conductor_intent_v53(g):
    if not g.notes:raise ValueError("empty graph")
    bounds=_section_boundaries(g)
    raw=[_section_features(g,a,b) for a,b in zip(bounds,bounds[1:])]
    energies=[_energy_metric(x) for x in raw]
    climax_idx=max(range(len(raw)),key=lambda i:energies[i])
    chars=_characterize(raw,climax_idx)
    start,end=bounds[0],bounds[-1];span=max(1,end-start)
    all_vib=[];all_rates=[];all_offs=[]
    for n in g.notes:
        all_vib.extend(_anchor_values(n,"vibrato_depth",float(n.cc3)/127.0))
        if float(getattr(n,"phrase_vibrato_rate_hz",0.0))>0:all_rates.append(float(n.phrase_vibrato_rate_hz))
        all_offs.append(float(getattr(n,"ensemble_attack_offset_ms",0.0)))
    sections=[]
    for i,(a,b,f,ch) in enumerate(zip(bounds,bounds[1:],raw,chars),1):
        # Ceiling permits expressive movement but protects macro hierarchy.
        headroom=.075 if ch=="climax" else (.06 if ch=="build" else .045)
        sections.append(SectionIntentV53(
            i,a,b,(a-start)/span,(b-start)/span,ch,
            f["dynamic_mean"],f["dynamic_peak"],min(1.0,f["dynamic_peak"]+headroom),
            f["vibrato_depth"],f["vibrato_rate_hz"],f["bow_pressure"],f["bow_reserve_floor"],
            f["desk_looseness_ms"],f["transition_density"],f["transition_treatment"],
            f["part_roles"],f["note_count"]
        ))
    plan=ConductorIntentV53(
        1,"5.3",start,end,climax_idx+1,
        ((bounds[climax_idx]+bounds[climax_idx+1])*.5-start)/span,
        min(1.0,max(x.dynamic_ceiling for x in sections)),
        mean(all_vib) if all_vib else 0.0,pstdev(all_vib) if len(all_vib)>1 else 0.0,
        mean(all_rates) if all_rates else 0.0,
        pstdev(all_offs) if len(all_offs)>1 else (abs(all_offs[0]) if all_offs else 0.0),
        sections
    )
    d=plan.as_dict();plan.intent_hash=_intent_hash(d)
    return plan

def _role_excess(target,observed):
    ex=0.0;hard=[]
    parts=set(target)|set(observed)
    for p in parts:
        t=target.get(p,{});o=observed.get(p,{})
        for role in ("lead","foundation"):
            tv=float(t.get(role,0.0));ov=float(o.get(role,0.0))
            if tv>=.60:
                drop=max(0.0,tv-ov-.18)
                ex=max(ex,drop/.32)
                if ov<.35:hard.append(f"part_{p}_{role}_lock_lost")
    return ex,hard

def evaluate_conductor_intent_v53(intent,g):
    sections=[];hard=[];max_ex=0.0;pen=0.0
    observed=[]
    for s in intent.sections:
        f=_section_features(g,s.start_tick,s.end_tick);observed.append(f)
        dyn_ex=max(
            max(0.0,abs(f["dynamic_mean"]-s.dynamic_mean)-.055)/.11,
            max(0.0,f["dynamic_peak"]-s.dynamic_ceiling)/.10
        )
        vib_ex=max(
            max(0.0,abs(f["vibrato_depth"]-s.vibrato_depth)-.07)/.12,
            max(0.0,abs(f["vibrato_rate_hz"]-s.vibrato_rate_hz)-.32)/.65 if s.vibrato_rate_hz>0 else 0.0
        )
        bow_ex=max(
            max(0.0,abs(f["bow_pressure"]-s.bow_pressure)-.07)/.14,
            max(0.0,(s.bow_reserve_floor-f["bow_reserve_floor"])-.10)/.25
        )
        desk_ex=max(0.0,abs(f["desk_looseness_ms"]-s.desk_looseness_ms)-.75)/2.4
        trans_ex=max(
            max(0.0,abs(f["transition_density"]-s.transition_density)-.16)/.34,
            max(0.0,abs(f["transition_treatment"]-s.transition_treatment)-.14)/.32
        )
        role_ex,role_hard=_role_excess(s.part_roles,f["part_roles"]);hard.extend(f"S{s.section_id}:{x}" for x in role_hard)
        ex={"dynamic":dyn_ex,"vibrato":vib_ex,"bow":bow_ex,"desk":desk_ex,"transition":trans_ex,"role":role_ex}
        wx=sum(DIM_WEIGHTS[k]*ex[k] for k in DIM_WEIGHTS)
        max_ex=max(max_ex,max(ex.values()) if ex else 0.0);pen+=wx
        sections.append(SectionAdherenceV53(
            s.section_id,s.character,{k:round(float(v),6) for k,v in ex.items()},round(wx,6),role_hard
        ))

    # Preserve intended macro climax. A repaired intro/build section may grow, but it may not
    # become a new climax unless the original macro energies were essentially tied.
    energies=[_energy_metric(x) for x in observed]
    obs_idx=max(range(len(energies)),key=lambda i:energies[i])
    intended=int(intent.climax_section_id)-1
    base_energies=[_energy_metric({
        "dynamic_mean":s.dynamic_mean,"dynamic_peak":s.dynamic_peak,
        "bow_pressure":s.bow_pressure,"vibrato_depth":s.vibrato_depth
    }) for s in intent.sections]
    if obs_idx!=intended:
        base_gap=base_energies[intended]-base_energies[obs_idx]
        if base_gap>.035 and energies[obs_idx]>energies[intended]+.018:
            hard.append(f"climax_shift_S{intent.climax_section_id}_to_S{obs_idx+1}")

    # Long-line direction lock: preserve meaningful build/release signs between macro sections.
    reversals=0
    for i in range(len(intent.sections)-1):
        bd=intent.sections[i+1].dynamic_mean-intent.sections[i].dynamic_mean
        od=observed[i+1]["dynamic_mean"]-observed[i]["dynamic_mean"]
        if abs(bd)>=.04 and bd*od<0 and abs(od)>=.02:
            reversals+=1;hard.append(f"long_line_direction_reversal_S{i+1}_S{i+2}")

    # Non-climax sections may not exceed the intended climax ceiling by a meaningful amount.
    climax_ceiling=float(intent.sections[intended].dynamic_ceiling)
    for i,(s,f) in enumerate(zip(intent.sections,observed)):
        if i==intended:continue
        if f["dynamic_peak"]>climax_ceiling+.04:
            hard.append(f"premature_dynamic_ceiling_S{s.section_id}")

    avg_pen=pen/max(1,len(sections))
    score=max(0.0,100.0-34.0*avg_pen-7.0*reversals-10.0*len(set(hard)))
    passed=score>=INTENT_PASS_SCORE and max_ex<=MAX_SECTION_EXCESS and not hard
    reason="pass" if passed else ("hard_section_lock" if hard else ("section_excess" if max_ex>MAX_SECTION_EXCESS else "intent_score"))
    return ConductorIntentReportV53(
        passed,round(score,6),round(max_ex,6),intent.climax_section_id,obs_idx+1,reversals,sorted(set(hard)),sections,reason
    )

def _section_for_tick(intent,tick):
    for s in intent.sections:
        if s.start_tick<=int(tick)<s.end_tick:return s
    return intent.sections[-1]

def _character_prior(slot,character):
    slot=str(slot).upper()
    if character=="climax":
        return {"C":.008,"B":.003,"A":-.002,"D":0.0}.get(slot,0.0)
    if character=="build":
        return {"C":.005,"B":.004,"A":0.0,"D":0.0}.get(slot,0.0)
    if character in ("intro","release","resolution"):
        return {"A":.005,"D":.003,"B":.001,"C":-.003}.get(slot,0.0)
    return {"B":.004,"A":.001,"C":.001,"D":0.0}.get(slot,0.0)

def choose_conductor_locked_decisions_v53(base_graph,candidate_graphs,decisions,intent=None):
    intent=intent or build_conductor_intent_v53(base_graph)
    if not decisions:
        coh=evaluate_global_coherence_v52(base_graph,base_graph,set())
        ir=evaluate_conductor_intent_v53(intent,base_graph)
        return [],coh,ir,{"searched":1,"overrides":0,"reason":"no_local_windows","intent_hash":intent.intent_hash}

    allowed=[_allowed_slots(d) for d in decisions]
    durations=[max(.05,float(d.get("duration_seconds",1.0))) for d in decisions]
    den=max(1e-9,sum(durations))
    best=None;searched=0;coherence_passed=0;intent_passed=0

    for combo in product(*allowed):
        searched+=1
        trial=[];audio=0.0;prior=0.0;overrides=0
        for d,slot,dur in zip(decisions,combo,durations):
            nd=dict(d);nd["local_winner"]=str(d.get("winner","D")).upper();nd["winner"]=str(slot).upper()
            if nd["winner"]!=nd["local_winner"]:overrides+=1
            sc=d.get("scores",{}).get(nd["winner"],{})
            audio+=dur*float(sc.get("overall",0.0))
            sec=_section_for_tick(intent,(int(d["start_tick"])+int(d["end_tick"]))//2)
            nd["conductor_section_id"]=sec.section_id;nd["conductor_character"]=sec.character
            prior+=dur*_character_prior(nd["winner"],sec.character)
            trial.append(nd)

        mg,modified=merge_graph_decisions_v52(base_graph,candidate_graphs,trial)
        coh=evaluate_global_coherence_v52(base_graph,mg,modified,COHERENCE_PASS,COHERENCE_EDGE)
        if not coh.passed:continue
        coherence_passed+=1
        ir=evaluate_conductor_intent_v53(intent,mg)
        if not ir.passed:continue
        intent_passed+=1
        audio/=den;prior/=den
        objective=audio+prior-.012*overrides+.00055*coh.score+.00075*ir.score
        item=(objective,ir.score,coh.score,-overrides,trial,coh,ir)
        if best is None or item[:4]>best[:4]:best=item

    if best is None:
        local=[dict(d,local_winner=str(d.get("winner","D")).upper()) for d in decisions]
        mg,modified=merge_graph_decisions_v52(base_graph,candidate_graphs,local)
        coh=evaluate_global_coherence_v52(base_graph,mg,modified,COHERENCE_PASS,COHERENCE_EDGE)
        ir=evaluate_conductor_intent_v53(intent,mg)
        return None,coh,ir,{
            "searched":searched,"coherence_passed":coherence_passed,"intent_passed":intent_passed,
            "overrides":None,"reason":"no_conductor_locked_candidate_combination","intent_hash":intent.intent_hash
        }

    trial,coh,ir=best[4],best[5],best[6]
    overrides=0
    for d in trial:
        changed=d["winner"]!=d["local_winner"];d["coherence_override"]=changed
        d["conductor_override"]=changed
        if changed:
            overrides+=1
            d["conductor_reason"]="long_form_section_character_lock"
        else:d["conductor_reason"]="local_winner_preserved"
    return trial,coh,ir,{
        "searched":searched,"coherence_passed":coherence_passed,"intent_passed":intent_passed,
        "overrides":overrides,"reason":"conductor_locked_combination_selected","intent_hash":intent.intent_hash
    }
