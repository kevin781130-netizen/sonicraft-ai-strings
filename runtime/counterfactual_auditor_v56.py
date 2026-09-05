"""SONICRAFT v5.6 Counterfactual Render Auditor / False-Prune Self-Calibration.

Audits Zero-Render decisions by periodically rendering the slots that the current candidate budget
would otherwise skip. The auditor calibrates *whether pruning is trusted*; it never changes notes,
performance controls, audio, or the acoustic model.

Core rules
----------
- Every context gets a deterministic prune-opportunity counter.
- Stable contexts audit approximately every 12 prune opportunities.
- Higher recent False-Prune Rate increases audit frequency to 6 or 4.
- A False Prune requires a previously pruned slot to become the full-evidence winner by >= 0.025
  Overall while clearing Safety/Overall floors.
- A context with repeated recent False Prunes disables predictor Zero-Render and falls back to the
  v5.4 primary budget. While disabled, counterfactual calibration is forced until recovery.
- Recovery requires four consecutive clean audits.
- Only aggregate counters / booleans / gains are persisted. No audio, MIDI, score text, filenames,
  user identity, or candidate-control data is stored.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import json,os,tempfile

SLOTS="ABCD"
PROFILE_VERSION=1
BASE_AUDIT_INTERVAL=12
ELEVATED_AUDIT_INTERVAL=6
HIGH_RISK_AUDIT_INTERVAL=4
FALSE_PRUNE_MARGIN=.025
SAFETY_FLOOR=.35
OVERALL_FLOOR=.35
RECENT_MAX=12
DISABLE_MIN_AUDITS=4
DISABLE_RATE=.25
RECOVERY_CLEAN_AUDITS=4


def default_audit_path_v56(utility_memory_path=None):
    if utility_memory_path:
        p=Path(utility_memory_path)
        return p.with_name(p.stem+".counterfactual_audit_v56.json")
    return Path.home()/".sonicraft"/"counterfactual_audit_v56.json"


def _clip(x,a=0.0,b=1.0):return max(a,min(b,float(x)))


def _score_value(sc,key):
    return float(sc[key] if isinstance(sc,dict) else getattr(sc,key))


@dataclass
class AuditPlanV56:
    context_key:str
    pruning_allowed:bool
    disabled_reason:str
    raw_predictor_confidence:float
    confidence_multiplier:float
    effective_confidence:float
    audit_interval:int
    prune_opportunity:int
    audit_due:bool
    initial_slots:list[str]
    pruned_slots:list[str]
    hypothetical_initial_slots:list[str]
    hypothetical_pruned_slots:list[str]
    audit_slots:list[str]
    reason:str
    def as_dict(self):return asdict(self)


class CounterfactualAuditMemoryV56:
    def __init__(self,path=None):
        self.path=Path(path) if path else default_audit_path_v56()
        self.contexts={};self.generation=0;self._load()

    def _load(self):
        try:
            o=json.loads(self.path.read_text(encoding="utf-8"))
            if int(o.get("version",0))!=PROFILE_VERSION:return
            self.contexts=dict(o.get("contexts",{}));self.generation=max(0,int(o.get("generation",0)))
        except Exception:return

    def _payload(self):
        return {
            "version":PROFILE_VERSION,"generation":self.generation,"contexts":self.contexts,
            "privacy":"aggregate audit outcomes only; no audio/MIDI/score text/file names/identity"
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

    def _ctx(self,key):
        return self.contexts.setdefault(str(key),{
            "prune_opportunities":0,"audits":0,"false_prunes":0,"near_misses":0,
            "recent":[],"disabled":False,"disabled_reason":"","clean_streak":0,
            "mean_counterfactual_gain":0.0,"max_counterfactual_gain":0.0,
        })

    def context(self,key):return dict(self._ctx(key))

    @staticmethod
    def recent_false_prune_rate(ctx):
        recent=list(ctx.get("recent",[]))[-RECENT_MAX:]
        if not recent:return 0.0
        return sum(1 for x in recent if bool(x.get("false_prune",False)))/float(len(recent))

    @staticmethod
    def recent_audits(ctx):return len(list(ctx.get("recent",[]))[-RECENT_MAX:])

    def calibration(self,key):
        ctx=self._ctx(key);rate=self.recent_false_prune_rate(ctx);n=self.recent_audits(ctx)
        disabled=bool(ctx.get("disabled",False))
        # Avoid overreacting to one early audit. Confidence degradation begins once >=2 audits exist.
        mult=1.0 if n<2 else max(.35,1.0-1.65*rate)
        if disabled:mult=min(mult,.42)
        if disabled:interval=1
        elif rate>=.20 and n>=3:interval=HIGH_RISK_AUDIT_INTERVAL
        elif rate>=.10 and n>=3:interval=ELEVATED_AUDIT_INTERVAL
        else:interval=BASE_AUDIT_INTERVAL
        return {
            "recent_false_prune_rate":rate,"recent_audits":n,"disabled":disabled,
            "disabled_reason":str(ctx.get("disabled_reason","") or ""),
            "confidence_multiplier":mult,"audit_interval":interval,
            "clean_streak":int(ctx.get("clean_streak",0)),
            "prune_opportunities":int(ctx.get("prune_opportunities",0)),
            "audits":int(ctx.get("audits",0)),"false_prunes":int(ctx.get("false_prunes",0)),
        }

    def plan(self,prediction,v54_primary):
        key=str(prediction.context_key);ctx=self._ctx(key);cal=self.calibration(key)
        raw=float(prediction.confidence);effective=_clip(raw*float(cal["confidence_multiplier"]))
        pruning_allowed=not cal["disabled"]

        # If audit calibration has reduced confidence below the predictor mode that created the
        # aggressive budget, fall back one step instead of trusting stale confidence.
        predicted_initial=list(prediction.initial_slots)
        v54=list(dict.fromkeys(v54_primary))
        if "D" not in v54:v54.append("D")
        if not pruning_allowed:
            initial=v54;reason="zero_render_disabled_v54_budget"
        elif effective<.48 and set(predicted_initial)!=set(v54):
            initial=v54;reason="audit_degraded_confidence_v54_budget"
        elif effective<.72 and len(predicted_initial)<=2:
            # High-confidence Top1+D is widened to predictor Top2+D under degraded calibration.
            non_d=[s for s in prediction.ranking if s!="D"]
            initial=list(dict.fromkeys(non_d[:2]+["D"]));reason="audit_degraded_top2_plus_D"
        else:
            initial=predicted_initial;reason="predictor_budget_allowed"

        if "D" not in initial:initial.append("D")
        pruned=[s for s in SLOTS if s not in initial]
        hypothetical_initial=list(dict.fromkeys(prediction.initial_slots))
        if "D" not in hypothetical_initial:hypothetical_initial.append("D")
        hypothetical_pruned=[s for s in SLOTS if s not in hypothetical_initial]
        # Calibration opportunities track what the predictor *would* prune, even when the auditor
        # has temporarily widened/disabled pruning and all four slots are already being rendered.
        opportunity=bool(hypothetical_pruned)
        if opportunity:
            ctx["prune_opportunities"]=int(ctx.get("prune_opportunities",0))+1
            self.generation+=1;self._save()
        cal=self.calibration(key)
        opp=int(ctx.get("prune_opportunities",0))
        interval=int(cal["audit_interval"])
        audit_due=bool(hypothetical_pruned) and (bool(cal["disabled"]) or (opp>0 and opp%interval==0))
        audit_slots=[s for s in SLOTS if s not in initial] if audit_due else []
        if audit_due:
            reason += "+counterfactual_audit_due"
        return AuditPlanV56(
            key,not bool(cal["disabled"]),str(cal["disabled_reason"]),raw,
            float(cal["confidence_multiplier"]),effective,interval,opp,audit_due,
            initial,pruned,hypothetical_initial,hypothetical_pruned,audit_slots,reason
        )

    def record_audit(self,key,preaudit_scores,preaudit_winner,full_scores,full_winner,pruned_slots):
        key=str(key);ctx=self._ctx(key);pre=str(preaudit_winner).upper();full=str(full_winner).upper()
        pruned={str(s).upper() for s in pruned_slots}
        pre_over=_score_value(full_scores[pre],"overall") if pre in full_scores else _score_value(preaudit_scores[pre],"overall")
        full_over=_score_value(full_scores[full],"overall")
        full_safe=_score_value(full_scores[full],"safety")
        gain=full_over-pre_over
        false_prune=(full in pruned and gain>=FALSE_PRUNE_MARGIN and full_safe>=SAFETY_FLOOR and full_over>=OVERALL_FLOOR)
        near_miss=(full in pruned and gain>0 and not false_prune)

        ctx["audits"]=int(ctx.get("audits",0))+1
        if false_prune:
            ctx["false_prunes"]=int(ctx.get("false_prunes",0))+1;ctx["clean_streak"]=0
        else:
            ctx["clean_streak"]=int(ctx.get("clean_streak",0))+1
        if near_miss:ctx["near_misses"]=int(ctx.get("near_misses",0))+1
        oldn=max(0,int(ctx["audits"])-1);oldm=float(ctx.get("mean_counterfactual_gain",0.0))
        ctx["mean_counterfactual_gain"]=(oldm*oldn+max(0.0,gain))/max(1,int(ctx["audits"]))
        ctx["max_counterfactual_gain"]=max(float(ctx.get("max_counterfactual_gain",0.0)),max(0.0,gain))
        recent=list(ctx.get("recent",[]));recent.append({
            "false_prune":bool(false_prune),"near_miss":bool(near_miss),
            "gain":round(float(gain),9),"preaudit_winner":pre,"full_winner":full,
        });ctx["recent"]=recent[-RECENT_MAX:]

        rate=self.recent_false_prune_rate(ctx);n=self.recent_audits(ctx)
        # Fast disable: 2 false prunes in the most recent 4 audits. Stable disable: >=25% after 4.
        r4=ctx["recent"][-4:];r4false=sum(1 for x in r4 if x.get("false_prune"))
        if (len(r4)>=4 and r4false>=2) or (n>=DISABLE_MIN_AUDITS and rate>=DISABLE_RATE):
            ctx["disabled"]=True
            ctx["disabled_reason"]="false_prune_rate_high"
        # Disabled contexts are fully calibrated every opportunity; 4 consecutive clean audits recover.
        if bool(ctx.get("disabled")) and int(ctx.get("clean_streak",0))>=RECOVERY_CLEAN_AUDITS:
            ctx["disabled"]=False;ctx["disabled_reason"]="";ctx["clean_streak"]=0
            # Recovery is based on a fresh clean calibration streak. Keep those clean audits as the
            # new recent window so stale failures do not immediately re-disable the context.
            ctx["recent"]=[x for x in ctx.get("recent",[])[-RECOVERY_CLEAN_AUDITS:] if not x.get("false_prune")]

        self.generation+=1;self._save();cal=self.calibration(key)
        return {
            "recorded":True,"context_key":key,"false_prune":bool(false_prune),
            "near_miss":bool(near_miss),"counterfactual_gain":round(float(gain),9),
            "preaudit_winner":pre,"full_winner":full,"pruned_slots":sorted(pruned),
            "recent_false_prune_rate":round(float(cal["recent_false_prune_rate"]),6),
            "confidence_multiplier":round(float(cal["confidence_multiplier"]),6),
            "audit_interval":int(cal["audit_interval"]),"disabled":bool(cal["disabled"]),
            "disabled_reason":str(cal["disabled_reason"]),"clean_streak":int(cal["clean_streak"]),
            "generation":self.generation,
        }
