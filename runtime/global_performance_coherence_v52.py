"""SONICRAFT v5.2 Global Performance Coherence Guard.

Protects against a classic local-optimization failure:
each repaired phrase can score better in isolation while the complete piece loses a coherent
performer/section identity.

The guard operates on ScoreGraph performance metadata, not audio. It compares the selectively
merged graph with D Original and penalizes *new* phrase-to-phrase discontinuities beyond the
original written/performance trajectory.

Dimensions:
- Dynamic trajectory
- Vibrato character (depth + rate)
- Bow energy (pressure + reserve)
- Desk looseness / ensemble attack spread
- Transition density/treatment
- Section role distribution

If the local Audio-Judge winner combination fails coherence, v5.2 searches nearby candidate
combinations (winner / near-runner / D) and selects the highest-audio-scoring combination that
passes the global guard. If none pass, the caller must fall back to full-song A/B/C/D.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field,fields
from copy import deepcopy
from itertools import product
from statistics import mean,pstdev

WEIGHTS={
    "dynamic_trajectory":.22,
    "vibrato_character":.18,
    "bow_energy":.20,
    "desk_looseness":.13,
    "transition_density":.17,
    "section_role":.10,
}
PASS_SCORE=82.0
MAX_EDGE_EXCESS=1.45
AUDIO_DROP_LIMIT=.075
IMMUTABLE={"part","start_tick","end_tick","pitch","velocity","voice","staff","source_id","lane_channel"}

@dataclass
class PhraseDescriptorV52:
    key:str
    part:int
    lane:int
    phrase_id:int
    start_tick:int
    end_tick:int
    source_ids:list[str]
    dynamic_mean:float
    dynamic_peak:float
    vibrato_depth:float
    vibrato_rate:float
    bow_pressure:float
    bow_reserve:float
    desk_looseness_ms:float
    transition_density:float
    transition_treatment:float
    role_lead:float
    role_inner:float
    role_foundation:float

@dataclass
class CoherenceEdgeV52:
    left_key:str
    right_key:str
    modified_boundary:bool
    dimension_excess:dict[str,float]
    weighted_excess:float

@dataclass
class CoherenceReportV52:
    passed:bool
    score:float
    max_edge_excess:float
    global_drift:dict[str,float]
    dimension_penalty:dict[str,float]
    edges:list[CoherenceEdgeV52]
    modified_phrase_keys:list[str]
    reason:str
    def as_dict(self):
        return {
            "schema":1,"version":"5.2","passed":self.passed,"score":round(float(self.score),6),
            "max_edge_excess":round(float(self.max_edge_excess),6),
            "global_drift":{k:round(float(v),6) for k,v in self.global_drift.items()},
            "dimension_penalty":{k:round(float(v),6) for k,v in self.dimension_penalty.items()},
            "modified_phrase_keys":self.modified_phrase_keys,"reason":self.reason,
            "edges":[asdict(x) for x in self.edges],
        }

def _clamp(x,a=0.0,b=1.0):return max(a,min(b,float(x)))

def phrase_key_v52(n):
    pid=int(getattr(n,"phrase_longline_id",0) or 0)
    if pid:return f"{int(n.part)}:{int(n.lane_channel)}:P{pid}"
    return f"{int(n.part)}:{int(n.lane_channel)}:N:{n.source_id}"

def _group(g):
    by={}
    for n in g.notes:by.setdefault(phrase_key_v52(n),[]).append(n)
    for ns in by.values():ns.sort(key=lambda n:(n.start_tick,n.pitch))
    return by

def _anchors(ns,key,fallback=0.0):
    vals=[]
    for n in ns:
        for a in getattr(n,"gesture_anchors",[]) or []:
            vals.append(float(a.get(key,fallback)))
    return vals

def _roles(ns):
    counts={"lead":0,"inner":0,"foundation":0};tot=0
    for n in ns:
        r=str(getattr(n,"ensemble_role","") or "")
        if r in counts:counts[r]+=1;tot+=1
    if not tot:return (0.,0.,0.)
    return tuple(counts[k]/tot for k in ("lead","inner","foundation"))

def describe_graph_v52(g):
    out={}
    for key,ns in _group(g).items():
        dyn=_anchors(ns,"dynamics_energy")
        vib=_anchors(ns,"vibrato_depth")
        dyn = dyn or [float(getattr(n,"cc1",80))/127.0 for n in ns]
        vib = vib or [float(getattr(n,"cc3",64))/127.0 for n in ns]
        rates=[float(getattr(n,"phrase_vibrato_rate_hz",0.0)) for n in ns if float(getattr(n,"phrase_vibrato_rate_hz",0.0))>0]
        pressures=[float(getattr(n,"bow_pressure",.5)) for n in ns]
        reserves=[float(getattr(n,"phrase_bow_reserve",1.0)) for n in ns]
        offsets=[float(getattr(n,"ensemble_attack_offset_ms",0.0)) for n in ns]
        trans=[n for n in ns if int(getattr(n,"transition_in_link_id",0) or 0)>0]
        density=len(trans)/max(1,len(ns))
        treatment=mean([_clamp(float(getattr(n,"transition_continuity",0.0)))*.65+
                        _clamp(float(getattr(n,"transition_duration_ms",0.0))/180.0)*.35 for n in trans]) if trans else 0.0
        lead,inner,foundation=_roles(ns)
        out[key]=PhraseDescriptorV52(
            key,int(ns[0].part),int(ns[0].lane_channel),int(getattr(ns[0],"phrase_longline_id",0) or 0),
            min(int(n.start_tick) for n in ns),max(int(n.end_tick) for n in ns),
            [str(n.source_id) for n in ns],
            mean(dyn),max(dyn),mean(vib),mean(rates) if rates else 0.0,
            mean(pressures),min(reserves),
            pstdev(offsets) if len(offsets)>1 else (abs(offsets[0]) if offsets else 0.0),
            density,treatment,lead,inner,foundation
        )
    return out

def _role_distance(a,b):
    return (abs(a.role_lead-b.role_lead)+abs(a.role_inner-b.role_inner)+abs(a.role_foundation-b.role_foundation))/2.0

def _feature_jump(a,b):
    return {
        "dynamic_trajectory":.68*abs(a.dynamic_mean-b.dynamic_mean)/.16+.32*abs(a.dynamic_peak-b.dynamic_peak)/.18,
        "vibrato_character":.62*abs(a.vibrato_depth-b.vibrato_depth)/.15+.38*abs(a.vibrato_rate-b.vibrato_rate)/.55,
        "bow_energy":.62*abs(a.bow_pressure-b.bow_pressure)/.14+.38*abs(a.bow_reserve-b.bow_reserve)/.25,
        "desk_looseness":abs(a.desk_looseness_ms-b.desk_looseness_ms)/2.2,
        "transition_density":.58*abs(a.transition_density-b.transition_density)/.35+.42*abs(a.transition_treatment-b.transition_treatment)/.28,
        "section_role":_role_distance(a,b)/.50,
    }

def _global_feature(desc):
    vals=list(desc.values())
    if not vals:return {k:0.0 for k in WEIGHTS}
    return {
        "dynamic_trajectory":mean(x.dynamic_mean for x in vals),
        "vibrato_character":mean((x.vibrato_depth/0.15)+(x.vibrato_rate/5.5)*.25 for x in vals),
        "bow_energy":mean((x.bow_pressure/.5)*.65+(1.0-x.bow_reserve)*.35 for x in vals),
        "desk_looseness":mean(x.desk_looseness_ms for x in vals),
        "transition_density":mean(x.transition_density*.6+x.transition_treatment*.4 for x in vals),
        "section_role":mean(x.role_lead+x.role_foundation for x in vals),
    }

def _global_drift(base,merged):
    b=_global_feature(base);m=_global_feature(merged)
    scales={"dynamic_trajectory":.10,"vibrato_character":.28,"bow_energy":.20,
            "desk_looseness":1.6,"transition_density":.18,"section_role":.18}
    return {k:abs(m[k]-b[k])/scales[k] for k in WEIGHTS}

def evaluate_global_coherence_v52(base_graph,merged_graph,modified_phrase_keys=None,
                                  pass_score=PASS_SCORE,max_edge_excess=MAX_EDGE_EXCESS):
    modified=set(modified_phrase_keys or [])
    b=describe_graph_v52(base_graph);m=describe_graph_v52(merged_graph)
    common=set(b)&set(m)
    lanes={}
    for key in common:
        d=b[key];lanes.setdefault((d.part,d.lane),[]).append(key)
    edges=[];dim_pen={k:0.0 for k in WEIGHTS};edge_count=0;max_ex=0.0

    for lane,keys in lanes.items():
        keys=sorted(keys,key=lambda k:(b[k].start_tick,b[k].end_tick))
        for lk,rk in zip(keys,keys[1:]):
            jb=_feature_jump(b[lk],b[rk]);jm=_feature_jump(m[lk],m[rk])
            boundary=(lk in modified) ^ (rk in modified)
            # New jumps are tolerated a little; boundaries between repaired and untouched phrases
            # receive tighter scrutiny.
            allowance=.12 if boundary else .20
            excess={k:max(0.0,jm[k]-jb[k]-allowance) for k in WEIGHTS}
            wx=sum(WEIGHTS[k]*excess[k] for k in WEIGHTS)
            if boundary:wx*=1.35
            max_ex=max(max_ex,max(excess.values()) if excess else 0.0)
            for k in WEIGHTS:dim_pen[k]+=WEIGHTS[k]*excess[k]*(1.35 if boundary else 1.0)
            edges.append(CoherenceEdgeV52(lk,rk,boundary,{k:round(v,6) for k,v in excess.items()},round(wx,6)))
            edge_count+=1

    drift=_global_drift(b,m)
    # Ignore small global character movement; repair is allowed to make the whole piece a little
    # cleaner. Penalize only larger style drift.
    drift_ex={k:max(0.0,drift[k]-.45) for k in WEIGHTS}
    local=sum(dim_pen.values())/max(1,edge_count)
    global_pen=sum(WEIGHTS[k]*drift_ex[k] for k in WEIGHTS)
    score=max(0.0,100.0-32.0*local-18.0*global_pen)
    passed=score>=float(pass_score) and max_ex<=float(max_edge_excess)
    reason="pass" if passed else ("edge_discontinuity" if max_ex>float(max_edge_excess) else "global_character_drift")
    return CoherenceReportV52(passed,round(score,6),round(max_ex,6),drift,dim_pen,edges,sorted(modified),reason)

def _copy_performance(dst,src):
    for f in fields(dst):
        if f.name in IMMUTABLE:continue
        setattr(dst,f.name,deepcopy(getattr(src,f.name)))

def _decision_selects_note(n,phrase_keys,start,end):
    if phrase_keys:
        internal=phrase_key_v52(n)
        pid=int(getattr(n,"phrase_longline_id",0) or 0)
        sid=str(n.source_id)
        for key in phrase_keys:
            key=str(key)
            if key==internal:return True
            if key==f"phrase:{pid}" and pid:return True
            if key==f"note:{sid}":return True
        return False
    return int(n.start_tick)<int(end) and int(n.end_tick)>int(start)

def merge_graph_decisions_v52(base_graph,candidate_graphs,decisions):
    out=deepcopy(base_graph)
    base_by={str(n.source_id):n for n in out.notes}
    cand_by={slot:{str(n.source_id):n for n in g.notes} for slot,g in candidate_graphs.items()}
    modified=set()
    for d in decisions:
        slot=str(d.get("winner","D")).upper()
        if slot=="D":continue
        if slot not in cand_by:raise ValueError(f"missing candidate graph {slot}")
        phrase_keys=set(d.get("phrase_keys",[]) or [])
        start=int(d["start_tick"]);end=int(d["end_tick"])
        for sid,dn in base_by.items():
            key=phrase_key_v52(dn)
            if not _decision_selects_note(dn,phrase_keys,start,end):continue
            sn=cand_by[slot].get(sid)
            if sn is None:continue
            _copy_performance(dn,sn);modified.add(key)
    return out,modified

def _allowed_slots(decision):
    scores=decision.get("scores",{})
    local=str(decision.get("winner","D")).upper()
    if local not in scores:
        return [local,"D"] if local!="D" else ["D"]
    best=float(scores[local]["overall"])
    ranked=sorted(scores.keys(),key=lambda s:float(scores[s]["overall"]),reverse=True)
    allowed=[local]
    # Keep only one near-scoring alternative; D is reserved as the third safety option.
    for s in ranked:
        s=str(s).upper()
        if s in (local,"D"):continue
        sc=scores[s]
        if float(sc["safety"])<.35 or float(sc["overall"])<.35:continue
        if best-float(sc["overall"])<=AUDIO_DROP_LIMIT:
            allowed.append(s);break
    if "D" in scores and float(scores["D"]["safety"])>=.35 and float(scores["D"]["overall"])>=.35:
        allowed.append("D")
    return list(dict.fromkeys(allowed))[:3]

def choose_coherent_decisions_v52(base_graph,candidate_graphs,decisions,
                                  pass_score=PASS_SCORE,max_edge_excess=MAX_EDGE_EXCESS):
    if not decisions:
        rep=evaluate_global_coherence_v52(base_graph,base_graph,set(),pass_score,max_edge_excess)
        return [],rep,{"searched":1,"overrides":0,"reason":"no_local_windows"}

    allowed=[_allowed_slots(d) for d in decisions]
    best=None;searched=0
    durations=[max(.05,float(d.get("duration_seconds",1.0))) for d in decisions]
    total_d=max(1e-9,sum(durations))

    for combo in product(*allowed):
        searched+=1
        trial=[]
        audio=0.0;overrides=0
        for d,s,dur in zip(decisions,combo,durations):
            nd=dict(d);nd["local_winner"]=str(d.get("winner","D")).upper();nd["winner"]=s
            if s!=nd["local_winner"]:overrides+=1
            sc=d.get("scores",{}).get(s,{})
            audio+=dur*float(sc.get("overall",0.0))
            trial.append(nd)
        mg,modified=merge_graph_decisions_v52(base_graph,candidate_graphs,trial)
        rep=evaluate_global_coherence_v52(base_graph,mg,modified,pass_score,max_edge_excess)
        if not rep.passed:continue
        audio/=total_d
        objective=audio-.012*overrides+.0007*rep.score
        item=(objective,rep.score,-overrides,trial,rep)
        if best is None or item[:3]>best[:3]:best=item

    if best is None:
        # Return the local-winner combination's diagnostic for an explicit fallback reason.
        mg,modified=merge_graph_decisions_v52(base_graph,candidate_graphs,decisions)
        rep=evaluate_global_coherence_v52(base_graph,mg,modified,pass_score,max_edge_excess)
        return None,rep,{"searched":searched,"overrides":None,"reason":"no_coherent_candidate_combination"}

    trial,rep=best[3],best[4]
    overrides=sum(1 for d in trial if d["winner"]!=d["local_winner"])
    for d in trial:
        if d["winner"]!=d["local_winner"]:
            d["coherence_override"]=True
            d["coherence_reason"]="global_performance_coherence"
        else:
            d["coherence_override"]=False
    return trial,rep,{"searched":searched,"overrides":overrides,"reason":"coherent_combination_selected"}
