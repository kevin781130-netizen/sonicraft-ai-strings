"""SONICRAFT v5.5 Candidate Utility Predictor / Zero-Render Pruning.

A tiny, explainable pre-render utility estimator. It never predicts audio samples and never trains
from skipped candidates. Only slots that were actually rendered + Audio-Judged may update memory.

Inputs:
- macro Section Character from v5.3
- localized v4.8 Critic dimensions
- v5.4 post-steer structural candidate scores
- current bounded Repair Policy
- optional local aggregate history from prior *actual* Audio Judge results

Safety:
- D Original is always rendered.
- no-history/low-confidence contexts fall back to the v5.4 primary candidate budget.
- strong history may reduce the first pass to predicted-best + D.
- any low Audio margin, safety/overall failure, or predictor-vs-audio winner disagreement escalates
  every pruned candidate before the window can be accepted.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,field
from pathlib import Path
import hashlib,json,math,os,tempfile

SLOTS="ABCD"
CORE_DIMS=("bow_reserve","transition","vibrato","dynamics_arc","gesture_spikes","ensemble_alignment","latent_playability")
PROFILE_VERSION=1
MIN_AUDIO_MARGIN=.025
HIGH_CONF=.72
MED_CONF=.48
HIGH_PRED_MARGIN=.12

CHAR_PRIOR={
 "intro":{"A":.68,"B":.64,"C":.46,"D":.58},
 "build":{"A":.55,"B":.70,"C":.72,"D":.54},
 "sustain":{"A":.58,"B":.73,"C":.62,"D":.56},
 "climax":{"A":.46,"B":.69,"C":.76,"D":.55},
 "release":{"A":.72,"B":.67,"C":.43,"D":.60},
 "resolution":{"A":.76,"B":.68,"C":.39,"D":.63},
}
DIM_PRIOR={
 "bow_reserve":{"A":.05,"B":.15,"C":.02,"D":-.08},
 "transition":{"A":.02,"B":.16,"C":.07,"D":-.08},
 "vibrato":{"A":.08,"B":.13,"C":.10,"D":-.07},
 "dynamics_arc":{"A":.04,"B":.12,"C":.14,"D":-.06},
 "gesture_spikes":{"A":.11,"B":.15,"C":.06,"D":-.07},
 "ensemble_alignment":{"A":.05,"B":.16,"C":.03,"D":-.06},
 "latent_playability":{"A":.03,"B":.12,"C":.03,"D":-.05},
}

def _clip(x,a=0.0,b=1.0):return max(a,min(b,float(x)))
def _sig(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()[:20]

def default_utility_path(policy_path=None):
    if policy_path:
        p=Path(policy_path)
        return p.with_name(p.stem+".candidate_utility_v55.json")
    return Path.home()/".sonicraft"/"candidate_utility_v55.json"

def context_key_v55(character,dimensions):
    dims=[]
    for d in dimensions or []:
        d=str(d)
        if d in CORE_DIMS and d not in dims:dims.append(d)
    dims=sorted(dims)[:3]
    return str(character)+"|"+("+".join(dims) if dims else "general")

@dataclass
class UtilityPredictionV55:
    context_key:str
    character:str
    dimensions:list[str]
    scores:dict[str,float]
    ranking:list[str]
    confidence:float
    predicted_margin:float
    memory_evidence:float
    initial_slots:list[str]
    pruned_slots:list[str]
    reason:str
    def as_dict(self):return asdict(self)

class CandidateUtilityMemoryV55:
    def __init__(self,path=None):
        self.path=Path(path) if path else default_utility_path()
        self.contexts={};self.generation=0;self._load()
    def _load(self):
        try:
            o=json.loads(self.path.read_text(encoding="utf-8"))
            if int(o.get("version",0))!=PROFILE_VERSION:return
            self.contexts=dict(o.get("contexts",{}));self.generation=max(0,int(o.get("generation",0)))
        except Exception:return
    def _payload(self):
        return {"version":PROFILE_VERSION,"generation":self.generation,"contexts":self.contexts,
                "privacy":"aggregates only; no audio/MIDI/score text/file names"}
    def snapshot(self):return self._payload()
    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(self._payload(),sort_keys=True,indent=2)+"\n"
        fd,tmp=tempfile.mkstemp(prefix=self.path.name+".",suffix=".tmp",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            try:os.unlink(tmp)
            except FileNotFoundError:pass
    def context(self,key):return self.contexts.get(str(key),{})
    def learn_rendered(self,key,scores,winner,full_evidence=False):
        rendered=[s for s in SLOTS if s in scores]
        if len(rendered)<2:return {"learned":False,"reason":"insufficient_rendered_slots"}
        winner=str(winner).upper()
        ctx=self.contexts.setdefault(str(key),{"total_windows":0.0,"slots":{}})
        weight=1.0 if full_evidence or len(rendered)==4 else .55
        ctx["total_windows"]=min(64.0,float(ctx.get("total_windows",0.0))+weight)
        for s in rendered:
            sc=scores[s]
            overall=float(sc["overall"] if isinstance(sc,dict) else sc.overall)
            safety=float(sc["safety"] if isinstance(sc,dict) else sc.safety)
            utility=.86*overall+.14*safety
            rec=ctx["slots"].setdefault(s,{"evidence":0.0,"utility":.5,"wins":0.0,"overall":.5,"safety":.5})
            olde=float(rec.get("evidence",0.0));a=min(.28,.08+weight/(4.0+olde))
            rec["utility"]=_clip(float(rec.get("utility",.5))*(1-a)+utility*a)
            rec["overall"]=_clip(float(rec.get("overall",.5))*(1-a)+overall*a)
            rec["safety"]=_clip(float(rec.get("safety",.5))*(1-a)+safety*a)
            rec["evidence"]=min(32.0,olde+weight)
            if s==winner:rec["wins"]=min(32.0,float(rec.get("wins",0.0))+weight)
        # Skipped slots are intentionally untouched.
        self.generation+=1;self._save()
        return {"learned":True,"reason":"actual_render_only","rendered":rendered,"generation":self.generation}

def _policy_bias(slot,policy):
    if not policy:return 0.0
    p={k:float(v) for k,v in policy.items()}
    if slot=="A":return .05*(1.0-p.get("smoothing",1.0))+.04*(1.0-p.get("expressive_apex",1.0))
    if slot=="B":return .05*(p.get("smoothing",1.0)-1.0)+.04*(p.get("transition",1.0)-1.0)+.03*(p.get("ensemble_tightness",1.0)-1.0)
    if slot=="C":return .055*(p.get("expressive_apex",1.0)-1.0)+.025*(1.0-p.get("ensemble_tightness",1.0))
    return 0.0

def predict_candidate_utility_v55(character,dimensions,steered_scores=None,repair_reports=None,policy=None,memory=None,v54_primary=None):
    character=str(character);dims=[d for d in (dimensions or []) if str(d) in CORE_DIMS]
    key=context_key_v55(character,dims)
    steered_scores=steered_scores or {};repair_reports=repair_reports or {}
    mem=(memory.context(key) if memory else {}) or {};slots_mem=mem.get("slots",{})
    scores={}
    structural_vals=[float(steered_scores.get(s,50.0)) for s in "ABC"]
    lo=min(structural_vals) if structural_vals else 0.;hi=max(structural_vals) if structural_vals else 1.;span=max(1.0,hi-lo)
    for s in SLOTS:
        u=float(CHAR_PRIOR.get(character,CHAR_PRIOR["sustain"])[s])
        for d in dims:u+=DIM_PRIOR.get(str(d),{}).get(s,0.0)/max(1,len(dims))
        if s in "ABC":
            u+=.10*((float(steered_scores.get(s,lo))-lo)/span-.5)
            rep=repair_reports.get(s)
            if rep is not None:u+=.0015*max(-20.0,min(30.0,float(getattr(rep,"improvement",0.0))))
        u+=_policy_bias(s,policy)
        mr=slots_mem.get(s)
        if mr:
            ev=float(mr.get("evidence",0.0));trust=min(.55,.10*ev)
            winrate=float(mr.get("wins",0.0))/max(.5,ev)
            hist=.70*float(mr.get("utility",.5))+.30*winrate
            u=(1-trust)*u+trust*hist
        scores[s]=_clip(u)
    ranking=sorted(SLOTS,key=lambda s:(scores[s],s=="D"),reverse=True)
    pred_margin=float(scores[ranking[0]]-scores[ranking[1]])
    evs=[float(slots_mem.get(s,{}).get("evidence",0.0)) for s in SLOTS]
    mem_evidence=sum(evs)/4.0
    completeness=sum(1 for e in evs if e>=2.0)/4.0
    confidence=_clip(.18+min(.52,mem_evidence*.07)+.22*completeness+min(.16,pred_margin*.8))

    # D is a mandatory baseline. A/B/C selection gets progressively tighter only with evidence.
    non_d=[s for s in ranking if s!="D"]
    primary=list(v54_primary or SLOTS)
    if confidence>=HIGH_CONF and pred_margin>=HIGH_PRED_MARGIN and mem_evidence>=3.0:
        initial=[non_d[0],"D"];reason="high_conf_top1_plus_D"
    elif confidence>=MED_CONF and mem_evidence>=1.5:
        initial=[non_d[0],non_d[1],"D"];reason="medium_conf_top2_plus_D"
    else:
        initial=list(primary);reason="v54_primary_fallback"
    initial=list(dict.fromkeys(initial))
    if "D" not in initial:initial.append("D")
    pruned=[s for s in SLOTS if s not in initial]
    return UtilityPredictionV55(key,character,sorted(set(map(str,dims))),{k:round(v,6) for k,v in scores.items()},ranking,
                                round(confidence,6),round(pred_margin,6),round(mem_evidence,6),initial,pruned,reason)

def should_escalate_v55(prediction,rendered_scores,winner,margin):
    if prediction is None:return False,"no_prediction"
    if float(margin)<MIN_AUDIO_MARGIN:return True,"low_audio_margin"
    predicted=next((s for s in prediction.ranking if s!="D"),prediction.ranking[0])
    if prediction.confidence>=MED_CONF and str(winner).upper()!=predicted:
        return True,"predictor_audio_disagreement"
    ws=rendered_scores[str(winner).upper()]
    safety=float(ws["safety"] if isinstance(ws,dict) else ws.safety)
    overall=float(ws["overall"] if isinstance(ws,dict) else ws.overall)
    if safety<.35:return True,"winner_safety_floor"
    if overall<.35:return True,"winner_overall_floor"
    return False,"accepted_initial_budget"
