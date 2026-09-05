"""SONICRAFT v5.8 Cross-Song Performance Archetype Memory.

This layer conditions candidate utility on a tiny D-derived performance-control archetype.

It is NOT genre recognition and does NOT store song identity. Labels such as Intimate / Ballad /
Dramatic / Chamber / Cinematic are deterministic names for control-envelope prototypes.

Persistent memory stores only aggregate rendered-candidate statistics grouped by:
    archetype label + Section Character + Critic context

It never stores audio, MIDI, score text, filenames, note sequences, or intent hashes.

Safety:
- D Original is never steered or pruned by archetype alone.
- archetype-only evidence can at most unlock Top2 + D.
- Top1 + D still requires target-context actual local evidence.
- audit False Prunes calibrate only archetype->context trust.
- low archetype classification confidence disables archetype transfer.
- skipped candidates never update archetype memory.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
from statistics import mean,pstdev
import json,math,os,tempfile

from candidate_utility_predictor_v55 import SLOTS,CORE_DIMS,_clip,context_key_v55,MED_CONF,HIGH_CONF,HIGH_PRED_MARGIN
from context_similarity_transfer_v57 import predict_candidate_utility_v57,UtilityPredictionV57

PROFILE_VERSION=1
ARCHETYPE_CONF_FLOOR=.42
ARCHETYPE_EVIDENCE_SCALE=.42
MAX_ARCHETYPE_EVIDENCE_PER_SLOT=4.0
ARCHETYPE_CONF_CAP_NO_LOCAL=.66
HIGH_LOCAL_EVIDENCE_FLOOR=1.5
EDGE_DISABLE_TRUST=.30
EDGE_RECOVERY_CLEAN=4

# Normalized performance-control prototypes.
# Labels are UX shorthand, not musicological genre classification.
PROTOTYPES={
    "intimate":{"dynamic":.42,"contrast":.17,"vibrato":.34,"rate":.46,"bow":.43,"desk":.30,"transition":.34,"role_focus":.58},
    "ballad":{"dynamic":.55,"contrast":.30,"vibrato":.48,"rate":.54,"bow":.50,"desk":.40,"transition":.46,"role_focus":.62},
    "dramatic":{"dynamic":.72,"contrast":.54,"vibrato":.65,"rate":.66,"bow":.66,"desk":.46,"transition":.67,"role_focus":.72},
    "chamber":{"dynamic":.51,"contrast":.24,"vibrato":.40,"rate":.50,"bow":.48,"desk":.72,"transition":.45,"role_focus":.42},
    "cinematic":{"dynamic":.66,"contrast":.44,"vibrato":.57,"rate":.60,"bow":.60,"desk":.34,"transition":.61,"role_focus":.78},
}
FEATURE_WEIGHTS={
    "dynamic":1.15,"contrast":1.05,"vibrato":.95,"rate":.70,
    "bow":.85,"desk":.65,"transition":.85,"role_focus":.70,
}


def default_archetype_path_v58(utility_memory_path=None):
    if utility_memory_path:
        p=Path(utility_memory_path)
        return p.with_name(p.stem+".performance_archetype_v58.json")
    return Path.home()/".sonicraft"/"performance_archetype_v58.json"


def _norm(x,a,b):
    if b<=a:return 0.0
    return _clip((float(x)-a)/(b-a))


def _role_focus(intent):
    vals=[]
    for s in intent.sections:
        for roles in (s.part_roles or {}).values():
            vals.append(max(float(roles.get("lead",0.0)),float(roles.get("foundation",0.0))))
    return mean(vals) if vals else .5


def archetype_features_v58(intent):
    secs=list(intent.sections)
    dyn=[float(s.dynamic_mean) for s in secs]
    peaks=[float(s.dynamic_peak) for s in secs]
    vib=[float(s.vibrato_depth) for s in secs]
    rates=[float(s.vibrato_rate_hz) for s in secs if float(s.vibrato_rate_hz)>0]
    bow=[float(s.bow_pressure) for s in secs]
    desk=[float(s.desk_looseness_ms) for s in secs]
    trans=[.58*float(s.transition_density)+.42*float(s.transition_treatment) for s in secs]
    contrast=(max(peaks)-min(dyn)) if dyn and peaks else 0.0
    return {
        "dynamic":round(_norm(mean(dyn) if dyn else .5,.30,.82),6),
        "contrast":round(_norm(contrast,.08,.58),6),
        "vibrato":round(_norm(mean(vib) if vib else .4,.18,.72),6),
        "rate":round(_norm(mean(rates) if rates else 5.0,4.3,6.2),6),
        "bow":round(_norm(mean(bow) if bow else .5,.34,.74),6),
        "desk":round(_norm(mean(desk) if desk else .8,.15,2.8),6),
        "transition":round(_norm(mean(trans) if trans else .4,.10,.80),6),
        "role_focus":round(_clip(_role_focus(intent)),6),
    }


@dataclass
class ArchetypeClassificationV58:
    label:str
    confidence:float
    secondary_label:str
    secondary_confidence:float
    features:dict
    distances:dict
    reason:str
    def as_dict(self):return asdict(self)


def classify_archetype_v58(intent):
    f=archetype_features_v58(intent)
    dist={}
    maxd=sum(FEATURE_WEIGHTS.values())
    for label,p in PROTOTYPES.items():
        d=0.0
        for k,w in FEATURE_WEIGHTS.items():
            d+=w*(float(f[k])-float(p[k]))**2
        dist[label]=math.sqrt(d/max(1e-9,maxd))
    ranking=sorted(dist,key=dist.get)
    a,b=ranking[:2]
    da,db=dist[a],dist[b]
    absolute=max(0.0,1.0-da/0.72)
    separation=max(0.0,min(1.0,(db-da)/0.22))
    confidence=_clip(.58*absolute+.42*separation)
    second=_clip(max(0.0,1.0-db/0.72)*.72)
    reason="prototype_match" if confidence>=ARCHETYPE_CONF_FLOOR else "low_confidence_control_profile"
    return ArchetypeClassificationV58(
        a,round(confidence,6),b,round(second,6),f,
        {k:round(v,6) for k,v in sorted(dist.items(),key=lambda kv:kv[1])},reason
    )


def _ctx_key(archetype,context_key):
    return f"{str(archetype)}::{str(context_key)}"


class PerformanceArchetypeMemoryV58:
    def __init__(self,path=None):
        self.path=Path(path) if path else default_archetype_path_v58()
        self.contexts={};self.edges={};self.generation=0;self._load()

    def _load(self):
        try:
            o=json.loads(self.path.read_text(encoding="utf-8"))
            if int(o.get("version",0))!=PROFILE_VERSION:return
            self.contexts=dict(o.get("contexts",{}));self.edges=dict(o.get("edges",{}))
            self.generation=max(0,int(o.get("generation",0)))
        except Exception:return

    def _payload(self):
        return {
            "version":PROFILE_VERSION,"generation":self.generation,
            "contexts":self.contexts,"edges":self.edges,
            "privacy":"aggregate control/archetype render statistics only; no audio/MIDI/score text/file names/note sequences/intent hashes",
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

    def context(self,archetype,context_key):
        return self.contexts.get(_ctx_key(archetype,context_key),{})

    def learn_rendered(self,archetype,context_key,scores,winner,classification_confidence=1.0,full_evidence=False):
        rendered=[s for s in SLOTS if s in scores]
        if len(rendered)<2:return {"learned":False,"reason":"insufficient_rendered_slots"}
        conf=_clip(classification_confidence)
        if conf<ARCHETYPE_CONF_FLOOR:return {"learned":False,"reason":"low_archetype_confidence"}
        winner=str(winner).upper()
        key=_ctx_key(archetype,context_key)
        ctx=self.contexts.setdefault(key,{"observations":0.0,"slots":{}})
        weight=(1.0 if full_evidence or len(rendered)==4 else .55)*(.55+.45*conf)
        ctx["observations"]=min(96.0,float(ctx.get("observations",0.0))+weight)
        for s in rendered:
            sc=scores[s]
            overall=float(sc["overall"] if isinstance(sc,dict) else sc.overall)
            safety=float(sc["safety"] if isinstance(sc,dict) else sc.safety)
            utility=.86*overall+.14*safety
            rec=ctx["slots"].setdefault(s,{"evidence":0.0,"utility":.5,"wins":0.0,"overall":.5,"safety":.5})
            old=float(rec.get("evidence",0.0));a=min(.22,.055+weight/(5.5+old))
            rec["utility"]=_clip((1-a)*float(rec.get("utility",.5))+a*utility)
            rec["overall"]=_clip((1-a)*float(rec.get("overall",.5))+a*overall)
            rec["safety"]=_clip((1-a)*float(rec.get("safety",.5))+a*safety)
            rec["evidence"]=min(40.0,old+weight)
            if s==winner:rec["wins"]=min(40.0,float(rec.get("wins",0.0))+weight)
        # skipped slots intentionally untouched
        self.generation+=1;self._save()
        return {"learned":True,"reason":"actual_render_only","rendered":rendered,
                "archetype":str(archetype),"context_key":str(context_key),"generation":self.generation}

    @staticmethod
    def edge_key(archetype,context_key):
        return f"{str(archetype)}->{str(context_key)}"

    def _edge(self,archetype,context_key):
        return self.edges.setdefault(self.edge_key(archetype,context_key),{
            "archetype":str(archetype),"context_key":str(context_key),"trust":1.0,
            "audits":0,"false_prunes":0,"clean_streak":0,"disabled":False,"recent":[],
            "max_false_prune_gain":0.0,
        })

    def calibration(self,archetype,context_key):
        e=self._edge(archetype,context_key)
        return {
            "trust":_clip(e.get("trust",1.0)),
            "disabled":bool(e.get("disabled",False)),
            "audits":int(e.get("audits",0)),
            "false_prunes":int(e.get("false_prunes",0)),
            "clean_streak":int(e.get("clean_streak",0)),
        }

    def record_audit(self,archetype,context_key,audit_record):
        if not audit_record:return {"recorded":False,"reason":"no_audit_record"}
        e=self._edge(archetype,context_key)
        false=bool(audit_record.get("false_prune",False))
        gain=max(0.0,float(audit_record.get("counterfactual_gain",0.0)))
        e["audits"]=int(e.get("audits",0))+1
        recent=list(e.get("recent",[]));recent.append({"false_prune":false,"gain":round(gain,9)})
        e["recent"]=recent[-8:]
        if false:
            e["false_prunes"]=int(e.get("false_prunes",0))+1;e["clean_streak"]=0
            e["trust"]=max(.15,float(e.get("trust",1.0))*(.56 if gain>=.05 else .66))
            e["max_false_prune_gain"]=max(float(e.get("max_false_prune_gain",0.0)),gain)
        else:
            e["clean_streak"]=int(e.get("clean_streak",0))+1
            e["trust"]=min(1.0,float(e.get("trust",1.0))+.045)
        r4=e["recent"][-4:];fails=sum(1 for x in r4 if x.get("false_prune"))
        if (len(r4)>=4 and fails>=2) or float(e["trust"])<=EDGE_DISABLE_TRUST:e["disabled"]=True
        if bool(e.get("disabled")) and int(e.get("clean_streak",0))>=EDGE_RECOVERY_CLEAN:
            e["disabled"]=False;e["clean_streak"]=0;e["trust"]=max(.55,float(e.get("trust",0.0)))
            e["recent"]=[x for x in e["recent"][-EDGE_RECOVERY_CLEAN:] if not x.get("false_prune")]
        self.generation+=1;self._save()
        return {"recorded":True,"false_prune":false,"gain":round(gain,9),
                "archetype":str(archetype),"context_key":str(context_key),
                "calibration":self.calibration(archetype,context_key),"generation":self.generation}


def collect_archetype_evidence_v58(classification,context_key,memory):
    if memory is None or classification is None:return {},{"accepted":False,"reason":"no_memory"}
    conf=float(classification.confidence)
    if conf<ARCHETYPE_CONF_FLOOR:
        return {},{"accepted":False,"reason":"low_archetype_confidence","confidence":conf}
    cal=memory.calibration(classification.label,context_key)
    if cal["disabled"]:
        return {},{"accepted":False,"reason":"archetype_context_disabled","calibration":cal}
    ctx=memory.context(classification.label,context_key) or {}
    slots=ctx.get("slots",{})
    trust=float(cal["trust"])*conf
    out={}
    for s in SLOTS:
        rec=slots.get(s)
        if not rec:continue
        ev=float(rec.get("evidence",0.0))
        if ev<.5:continue
        eff=min(MAX_ARCHETYPE_EVIDENCE_PER_SLOT,ev*ARCHETYPE_EVIDENCE_SCALE*trust)
        out[s]={
            "evidence":eff,
            "utility":float(rec.get("utility",.5)),
            "overall":float(rec.get("overall",.5)),
            "safety":float(rec.get("safety",.5)),
            "winrate":float(rec.get("wins",0.0))/max(.5,ev),
        }
    return out,{
        "accepted":bool(out),"reason":"accepted" if out else "no_archetype_evidence",
        "archetype":classification.label,"classification_confidence":conf,
        "edge_trust":float(cal["trust"]),"effective_trust":trust,
        "raw_observations":float(ctx.get("observations",0.0)),
    }


@dataclass
class UtilityPredictionV58:
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
    archetype_label:str
    archetype_classification_confidence:float
    archetype_evidence:float
    archetype_confidence:float
    archetype_detail:dict
    initial_slots:list[str]
    pruned_slots:list[str]
    reason:str
    def as_dict(self):return asdict(self)


def predict_candidate_utility_v58(character,dimensions,steered_scores=None,repair_reports=None,policy=None,
                                  utility_memory=None,audit_memory=None,transfer_memory=None,
                                  archetype_memory=None,archetype_classification=None,v54_primary=None):
    base=predict_candidate_utility_v57(
        character,dimensions,steered_scores,repair_reports,policy,
        utility_memory,audit_memory,transfer_memory,v54_primary
    )
    arche,detail=collect_archetype_evidence_v58(archetype_classification,base.context_key,archetype_memory)
    scores=dict(base.scores)
    evs=[]
    for s in SLOTS:
        rec=arche.get(s)
        if not rec:continue
        ev=float(rec.get("evidence",0.0));evs.append(ev)
        hist=.70*float(rec.get("utility",.5))+.30*float(rec.get("winrate",0.0))
        trust=min(.22,.045*ev) # archetype evidence is weaker than exact/similarity evidence
        scores[s]=_clip((1-trust)*float(scores[s])+trust*hist)

    ranking=sorted(SLOTS,key=lambda s:(scores[s],s=="D"),reverse=True)
    pred_margin=float(scores[ranking[0]]-scores[ranking[1]])
    arche_ev=sum(evs)/4.0 if evs else 0.0
    arch_conf=0.0
    if detail.get("accepted"):
        arch_conf=_clip(min(1.0,arche_ev/3.0)*float(detail.get("effective_trust",0.0)))
    effective_ev=float(base.memory_evidence)+.75*arche_ev
    confidence=_clip(float(base.confidence)+min(.40,.18*arche_ev)*float(detail.get("effective_trust",0.0)))
    # Cross-song archetype evidence cannot by itself cause Top1+D.
    if float(base.local_evidence)<.5 and float(base.transfer_evidence)<.5:
        confidence=min(confidence,ARCHETYPE_CONF_CAP_NO_LOCAL)

    non_d=[s for s in ranking if s!="D"]
    primary=list(v54_primary or SLOTS)
    if (float(base.local_evidence)>=HIGH_LOCAL_EVIDENCE_FLOOR and
        confidence>=HIGH_CONF and pred_margin>=HIGH_PRED_MARGIN and effective_ev>=3.0):
        initial=[non_d[0],"D"];reason="archetype_hybrid_high_conf_top1_plus_D"
    elif confidence>=MED_CONF and effective_ev>=1.5:
        initial=[non_d[0],non_d[1],"D"]
        reason="archetype_cross_song_top2_plus_D" if arche_ev>0 else base.reason
    else:
        initial=list(base.initial_slots);reason=base.reason
    initial=list(dict.fromkeys(initial))
    if "D" not in initial:initial.append("D")
    pruned=[s for s in SLOTS if s not in initial]
    return UtilityPredictionV58(
        base.context_key,base.character,base.dimensions,{k:round(float(v),6) for k,v in scores.items()},
        ranking,round(confidence,6),round(pred_margin,6),round(effective_ev,6),
        float(base.local_evidence),float(base.transfer_evidence),float(base.transfer_confidence),
        list(base.transfer_donors),list(base.transfer_detail),
        str(getattr(archetype_classification,"label","unknown")),
        float(getattr(archetype_classification,"confidence",0.0)),
        round(arche_ev,6),round(arch_conf,6),detail,initial,pruned,reason
    )
