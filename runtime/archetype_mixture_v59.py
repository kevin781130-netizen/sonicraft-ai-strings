"""SONICRAFT v5.9 Multi-Archetype Mixture / Soft Classification.

v5.8 assigned one primary performance-control archetype. v5.9 keeps that backward-compatible
classification but uses a soft mixture of up to three nearby prototypes for cross-song evidence.

This is still NOT genre recognition. All weights are derived from D Original aggregate controls.

Persistent layers remain isolated:
- v5.5 exact Candidate Utility Memory
- v5.7 target<-donor Similarity Transfer edges
- v5.8 aggregate per-archetype rendered evidence
- v5.9 mixture-component->context trust

Safety:
- low whole-profile fit blocks mixture evidence;
- D Original remains mandatory;
- mixture-only evidence can at most unlock Top2+D;
- Top1+D still requires real target-context evidence;
- only actually rendered slots update component evidence;
- Counterfactual False Prunes penalize only mixture component->context edges.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import json,math,os,tempfile

from candidate_utility_predictor_v55 import SLOTS,_clip,MED_CONF,HIGH_CONF,HIGH_PRED_MARGIN
from context_similarity_transfer_v57 import predict_candidate_utility_v57
from performance_archetype_memory_v58 import (
    PROTOTYPES,FEATURE_WEIGHTS,ARCHETYPE_CONF_FLOOR,HIGH_LOCAL_EVIDENCE_FLOOR,
    archetype_features_v58,classify_archetype_v58,PerformanceArchetypeMemoryV58
)

PROFILE_VERSION=1
SOFTMAX_TEMP=.105
MAX_COMPONENTS=3
MIN_COMPONENT_WEIGHT=.08
MIXTURE_CONF_FLOOR=.42
MIXTURE_CONF_CAP_NO_LOCAL=.66
MIXTURE_EVIDENCE_SCALE=.40
MAX_MIXTURE_EVIDENCE_PER_SLOT=4.0
COMPONENT_EDGE_DISABLE_TRUST=.30
COMPONENT_EDGE_RECOVERY_CLEAN=4


@dataclass
class MixtureComponentV59:
    label:str
    weight:float
    distance:float

@dataclass
class ArchetypeMixtureV59:
    components:list[MixtureComponentV59]
    confidence:float
    weighted_distance:float
    entropy:float
    primary_label:str
    legacy_primary_confidence:float
    features:dict
    distances:dict
    reason:str
    def as_dict(self):return {
        "components":[asdict(x) for x in self.components],
        "confidence":self.confidence,
        "weighted_distance":self.weighted_distance,
        "entropy":self.entropy,
        "primary_label":self.primary_label,
        "legacy_primary_confidence":self.legacy_primary_confidence,
        "features":self.features,
        "distances":self.distances,
        "reason":self.reason,
    }


def mixture_from_distances_v59(features,distances,legacy_primary_confidence=0.0):
    ranking=sorted(distances,key=distances.get)[:MAX_COMPONENTS]
    d0=float(distances[ranking[0]])
    raw={k:math.exp(-(float(distances[k])-d0)/SOFTMAX_TEMP) for k in ranking}
    den=max(1e-12,sum(raw.values()))
    weights={k:v/den for k,v in raw.items()}
    kept={k:v for k,v in weights.items() if v>=MIN_COMPONENT_WEIGHT}
    if not kept:kept={ranking[0]:1.0}
    den=max(1e-12,sum(kept.values()))
    kept={k:v/den for k,v in kept.items()}
    weighted=sum(float(distances[k])*w for k,w in kept.items())
    entropy=-sum(w*math.log(max(w,1e-12)) for w in kept.values())
    entropy_norm=entropy/max(1e-12,math.log(max(2,len(kept)))) if len(kept)>1 else 0.0

    # Unlike the v5.8 hard-label confidence, ambiguity between nearby prototypes is not itself bad.
    # Mixture confidence measures whether the whole D-derived control profile lies near the prototype manifold.
    fit=_clip(1.0-weighted/.72)
    nearest_fit=_clip(1.0-d0/.72)
    confidence=_clip(.66*fit+.34*nearest_fit)
    reason="soft_mixture_fit" if confidence>=MIXTURE_CONF_FLOOR else "low_confidence_control_manifold"
    comps=[MixtureComponentV59(k,round(w,6),round(float(distances[k]),6))
           for k,w in sorted(kept.items(),key=lambda kv:kv[1],reverse=True)]
    return ArchetypeMixtureV59(
        comps,round(confidence,6),round(weighted,6),round(entropy_norm,6),
        comps[0].label,round(float(legacy_primary_confidence),6),
        dict(features),{k:round(float(v),6) for k,v in sorted(distances.items(),key=lambda kv:kv[1])},reason
    )


def soft_classify_archetype_v59(intent):
    legacy=classify_archetype_v58(intent)
    return mixture_from_distances_v59(legacy.features,legacy.distances,legacy.confidence)


def default_mixture_path_v59(utility_memory_path=None):
    if utility_memory_path:
        p=Path(utility_memory_path)
        return p.with_name(p.stem+".archetype_mixture_v59.json")
    return Path.home()/".sonicraft"/"archetype_mixture_v59.json"


class ArchetypeMixtureMemoryV59:
    """Stores only component->target-context calibration, never song or candidate evidence."""
    def __init__(self,path=None):
        self.path=Path(path) if path else default_mixture_path_v59()
        self.edges={};self.generation=0;self._load()

    def _load(self):
        try:
            o=json.loads(self.path.read_text(encoding="utf-8"))
            if int(o.get("version",0))!=PROFILE_VERSION:return
            self.edges=dict(o.get("edges",{}));self.generation=max(0,int(o.get("generation",0)))
        except Exception:return

    def _payload(self):
        return {
            "version":PROFILE_VERSION,"generation":self.generation,"edges":self.edges,
            "privacy":"component-to-context aggregate calibration only; no audio/MIDI/score text/file names/note sequences/song identity/intent hashes"
        }

    def snapshot(self):return self._payload()

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(self._payload(),sort_keys=True,indent=2)+"\n"
        fd,tmp=tempfile.mkstemp(prefix=self.path.name+".",suffix=".tmp",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            try:os.unlink(tmp)
            except FileNotFoundError:pass

    @staticmethod
    def edge_key(label,context_key):return f"{str(label)}->{str(context_key)}"

    def _edge(self,label,context_key):
        return self.edges.setdefault(self.edge_key(label,context_key),{
            "label":str(label),"context_key":str(context_key),"trust":1.0,
            "audits":0,"false_prunes":0,"clean_streak":0,"disabled":False,
            "recent":[],"max_false_prune_gain":0.0,
        })

    def calibration(self,label,context_key):
        e=self._edge(label,context_key)
        return {
            "trust":_clip(e.get("trust",1.0)),"disabled":bool(e.get("disabled",False)),
            "audits":int(e.get("audits",0)),"false_prunes":int(e.get("false_prunes",0)),
            "clean_streak":int(e.get("clean_streak",0)),
        }

    def record_audit(self,context_key,components,audit_record):
        if not audit_record:return {"recorded":False,"reason":"no_audit_record"}
        comps=[c for c in components or [] if float(c.get("weight",0.0))>=MIN_COMPONENT_WEIGHT]
        if not comps:return {"recorded":False,"reason":"no_active_components"}
        false=bool(audit_record.get("false_prune",False))
        gain=max(0.0,float(audit_record.get("counterfactual_gain",0.0)))
        rows=[]
        for c in comps:
            label=str(c["label"]);w=_clip(c["weight"])
            e=self._edge(label,context_key);e["audits"]=int(e.get("audits",0))+1
            recent=list(e.get("recent",[]));recent.append({"false_prune":false,"gain":round(gain,9),"weight":round(w,6)})
            e["recent"]=recent[-8:]
            if false:
                e["false_prunes"]=int(e.get("false_prunes",0))+1;e["clean_streak"]=0
                full_factor=.56 if gain>=.05 else .66
                factor=1.0-(1.0-full_factor)*w
                e["trust"]=max(.15,float(e.get("trust",1.0))*factor)
                e["max_false_prune_gain"]=max(float(e.get("max_false_prune_gain",0.0)),gain)
            else:
                e["clean_streak"]=int(e.get("clean_streak",0))+1
                e["trust"]=min(1.0,float(e.get("trust",1.0))+.045*w)
            r4=e["recent"][-4:];fails=sum(1 for x in r4 if x.get("false_prune"))
            if (len(r4)>=4 and fails>=2) or float(e["trust"])<=COMPONENT_EDGE_DISABLE_TRUST:e["disabled"]=True
            if bool(e.get("disabled")) and int(e.get("clean_streak",0))>=COMPONENT_EDGE_RECOVERY_CLEAN:
                e["disabled"]=False;e["clean_streak"]=0;e["trust"]=max(.55,float(e.get("trust",0.0)))
                e["recent"]=[x for x in e["recent"][-COMPONENT_EDGE_RECOVERY_CLEAN:] if not x.get("false_prune")]
            rows.append({"label":label,"weight":round(w,6),**self.calibration(label,context_key)})
        self.generation+=1;self._save()
        return {"recorded":True,"context_key":str(context_key),"false_prune":false,
                "gain":round(gain,9),"components":rows,"generation":self.generation}


def _slot_record(ctx,slot):
    return ((ctx or {}).get("slots",{}) or {}).get(slot)


def collect_mixture_evidence_v59(mixture,context_key,archetype_memory,mixture_memory):
    if mixture is None or archetype_memory is None:
        return {},{"accepted":False,"reason":"no_mixture_memory","components":[]}
    if float(mixture.confidence)<MIXTURE_CONF_FLOOR:
        return {},{"accepted":False,"reason":"low_mixture_confidence","components":[]}
    acc={s:{"w":0.0,"utility":0.0,"overall":0.0,"safety":0.0,"winrate":0.0,"evidence":0.0} for s in SLOTS}
    details=[]
    for comp in mixture.components:
        label=str(comp.label);mixw=float(comp.weight)
        oldcal=archetype_memory.calibration(label,context_key)
        newcal=mixture_memory.calibration(label,context_key) if mixture_memory is not None else {"trust":1.0,"disabled":False}
        disabled=bool(oldcal.get("disabled",False) or newcal.get("disabled",False))
        trust=float(oldcal.get("trust",1.0))*float(newcal.get("trust",1.0))*float(mixture.confidence)*mixw
        ctx=archetype_memory.context(label,context_key) or {}
        accepted=False
        if not disabled and trust>.02:
            for s in SLOTS:
                rec=_slot_record(ctx,s)
                if not rec:continue
                raw_ev=float(rec.get("evidence",0.0))
                if raw_ev<.5:continue
                eff=min(MAX_MIXTURE_EVIDENCE_PER_SLOT,raw_ev*MIXTURE_EVIDENCE_SCALE*trust)
                if eff<=0:continue
                wr=float(rec.get("wins",0.0))/max(.5,raw_ev)
                a=acc[s];a["w"]+=eff;a["evidence"]+=eff
                a["utility"]+=eff*float(rec.get("utility",.5))
                a["overall"]+=eff*float(rec.get("overall",.5))
                a["safety"]+=eff*float(rec.get("safety",.5))
                a["winrate"]+=eff*wr
                accepted=True
        details.append({
            "label":label,"weight":round(mixw,6),"distance":round(float(comp.distance),6),
            "v58_edge_trust":round(float(oldcal.get("trust",1.0)),6),
            "v59_component_trust":round(float(newcal.get("trust",1.0)),6),
            "effective_weight":round(trust,6),"disabled":disabled,"accepted":accepted,
        })
    out={}
    for s,a in acc.items():
        if a["w"]<=0:continue
        out[s]={
            "evidence":min(MAX_MIXTURE_EVIDENCE_PER_SLOT,a["evidence"]),
            "utility":a["utility"]/a["w"],"overall":a["overall"]/a["w"],
            "safety":a["safety"]/a["w"],"winrate":a["winrate"]/a["w"],
        }
    return out,{
        "accepted":bool(out),"reason":"accepted" if out else "no_component_evidence",
        "mixture_confidence":float(mixture.confidence),"components":details,
    }


def learn_mixture_rendered_v59(archetype_memory,mixture,context_key,scores,winner,full_evidence=False):
    """Write weighted actual-render evidence into the existing v5.8 per-archetype aggregate store."""
    rendered=[s for s in SLOTS if s in scores]
    if len(rendered)<2:return {"learned":False,"reason":"insufficient_rendered_slots"}
    if mixture is None or float(mixture.confidence)<MIXTURE_CONF_FLOOR:
        return {"learned":False,"reason":"low_mixture_confidence"}
    winner=str(winner).upper()
    base_weight=1.0 if full_evidence or len(rendered)==4 else .55
    rows=[]
    for comp in mixture.components:
        cw=float(comp.weight)
        if cw<MIN_COMPONENT_WEIGHT:continue
        weight=base_weight*float(mixture.confidence)*cw
        if weight<.03:continue
        key=f"{str(comp.label)}::{str(context_key)}"
        ctx=archetype_memory.contexts.setdefault(key,{"observations":0.0,"slots":{}})
        ctx["observations"]=min(96.0,float(ctx.get("observations",0.0))+weight)
        for s in rendered:
            sc=scores[s]
            overall=float(sc["overall"] if isinstance(sc,dict) else sc.overall)
            safety=float(sc["safety"] if isinstance(sc,dict) else sc.safety)
            utility=.86*overall+.14*safety
            rec=ctx["slots"].setdefault(s,{"evidence":0.0,"utility":.5,"wins":0.0,"overall":.5,"safety":.5})
            old=float(rec.get("evidence",0.0));a=min(.20,.045+weight/(6.0+old))
            rec["utility"]=_clip((1-a)*float(rec.get("utility",.5))+a*utility)
            rec["overall"]=_clip((1-a)*float(rec.get("overall",.5))+a*overall)
            rec["safety"]=_clip((1-a)*float(rec.get("safety",.5))+a*safety)
            rec["evidence"]=min(40.0,old+weight)
            if s==winner:rec["wins"]=min(40.0,float(rec.get("wins",0.0))+weight)
        rows.append({"label":comp.label,"weight":round(cw,6),"effective_learning_weight":round(weight,6)})
    if not rows:return {"learned":False,"reason":"no_active_components"}
    archetype_memory.generation+=1;archetype_memory._save()
    return {"learned":True,"reason":"actual_render_only_soft_mixture",
            "rendered":rendered,"components":rows,"generation":archetype_memory.generation}


@dataclass
class UtilityPredictionV59:
    context_key:str
    character:str
    dimensions:list[str]
    scores:dict[str,float]
    ranking:list[str]
    confidence:float
    predicted_margin:float
    memory_evidence:float
    local_evidence:float
    transfer_evidence:float
    transfer_confidence:float
    transfer_donors:list[str]
    transfer_detail:list[dict]
    mixture_confidence:float
    mixture_evidence:float
    mixture_components:list[dict]
    mixture_detail:dict
    initial_slots:list[str]
    pruned_slots:list[str]
    reason:str
    def as_dict(self):return asdict(self)


def predict_candidate_utility_v59(character,dimensions,steered_scores=None,repair_reports=None,policy=None,
                                  utility_memory=None,audit_memory=None,transfer_memory=None,
                                  archetype_memory=None,mixture_memory=None,archetype_mixture=None,
                                  v54_primary=None):
    base=predict_candidate_utility_v57(
        character,dimensions,steered_scores,repair_reports,policy,
        utility_memory,audit_memory,transfer_memory,v54_primary
    )
    mix,detail=collect_mixture_evidence_v59(archetype_mixture,base.context_key,archetype_memory,mixture_memory)
    scores=dict(base.scores);evs=[]
    for s in SLOTS:
        rec=mix.get(s)
        if not rec:continue
        ev=float(rec.get("evidence",0.0));evs.append(ev)
        hist=.70*float(rec.get("utility",.5))+.30*float(rec.get("winrate",0.0))
        trust=min(.22,.045*ev)
        scores[s]=_clip((1-trust)*float(scores[s])+trust*hist)
    ranking=sorted(SLOTS,key=lambda s:(scores[s],s=="D"),reverse=True)
    pred_margin=float(scores[ranking[0]]-scores[ranking[1]])
    mix_ev=sum(evs)/4.0 if evs else 0.0
    effective_ev=float(base.memory_evidence)+.85*mix_ev
    confidence=_clip(float(base.confidence)+min(.40,.18*mix_ev)*float(getattr(archetype_mixture,"confidence",0.0)))
    if float(base.local_evidence)<.5 and float(base.transfer_evidence)<.5:
        confidence=min(confidence,MIXTURE_CONF_CAP_NO_LOCAL)

    non_d=[s for s in ranking if s!="D"]
    if (float(base.local_evidence)>=HIGH_LOCAL_EVIDENCE_FLOOR and confidence>=HIGH_CONF
        and pred_margin>=HIGH_PRED_MARGIN and effective_ev>=3.0):
        initial=[non_d[0],"D"];reason="mixture_hybrid_high_conf_top1_plus_D"
    elif confidence>=MED_CONF and effective_ev>=1.5:
        initial=[non_d[0],non_d[1],"D"]
        reason="soft_archetype_mixture_top2_plus_D" if mix_ev>0 else base.reason
    else:
        initial=list(base.initial_slots);reason=base.reason
    initial=list(dict.fromkeys(initial))
    if "D" not in initial:initial.append("D")
    pruned=[s for s in SLOTS if s not in initial]
    return UtilityPredictionV59(
        base.context_key,base.character,base.dimensions,{k:round(float(v),6) for k,v in scores.items()},
        ranking,round(confidence,6),round(pred_margin,6),round(effective_ev,6),
        float(base.local_evidence),float(base.transfer_evidence),float(base.transfer_confidence),
        list(base.transfer_donors),list(base.transfer_detail),
        float(getattr(archetype_mixture,"confidence",0.0)),round(mix_ev,6),
        [asdict(c) for c in getattr(archetype_mixture,"components",[])],detail,
        initial,pruned,reason
    )
