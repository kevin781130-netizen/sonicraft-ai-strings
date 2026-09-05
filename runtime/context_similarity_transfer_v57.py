"""SONICRAFT v5.7 Context Generalization / Similarity Transfer.

Transfers *discounted* Candidate Utility evidence between similar contexts so a new phrase does not
need to rebuild all evidence from zero. This is not a learned embedding or black-box model.

Hard isolation:
- Section Character must match exactly.
- Critic dimension sets must overlap; unrelated problem types never transfer.
- donor Counterfactual Audit disable/high-risk state blocks or discounts transfer.
- transfer-edge trust is stored separately from donor local Utility/Audit memory.
- a transfer False Prune penalizes only target<-donor edges, never the donor's own local context.
- transfer-only evidence can at most unlock Top2+D. Top1+D requires actual target-context evidence.
- skipped candidates still never update Candidate Utility Memory.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import json,math,os,tempfile

from candidate_utility_predictor_v55 import (
    SLOTS,CORE_DIMS,CHAR_PRIOR,DIM_PRIOR,_clip,_policy_bias,context_key_v55,
    HIGH_CONF,MED_CONF,HIGH_PRED_MARGIN
)

PROFILE_VERSION=1
MIN_JACCARD=.34
MIN_DONOR_SLOT_EVIDENCE=1.5
TRANSFER_EVIDENCE_SCALE=.32
MAX_TRANSFER_EVIDENCE_PER_SLOT=4.0
TRANSFER_CONF_CAP_NO_LOCAL=.68
HIGH_LOCAL_EVIDENCE_FLOOR=1.5
EDGE_DISABLE_TRUST=.30
EDGE_RECOVERY_CLEAN=4


def default_transfer_path_v57(utility_memory_path=None):
    if utility_memory_path:
        p=Path(utility_memory_path)
        return p.with_name(p.stem+'.context_transfer_v57.json')
    return Path.home()/'.sonicraft'/'context_transfer_v57.json'


def _parse_key(key):
    s=str(key)
    if '|' not in s:return s,set()
    char,d=s.split('|',1)
    dims=set() if d in ('','general') else {x for x in d.split('+') if x in CORE_DIMS}
    return char,dims


def context_similarity_v57(target_key,donor_key):
    tc,td=_parse_key(target_key);dc,dd=_parse_key(donor_key)
    if tc!=dc:return 0.0
    if not td or not dd:return 0.0
    inter=len(td&dd);union=len(td|dd)
    if inter<=0 or union<=0:return 0.0
    j=inter/float(union)
    if j<MIN_JACCARD:return 0.0
    # Exact contexts are local evidence, not transfer evidence.
    if td==dd:return 0.0
    subset_bonus=.08 if (td<=dd or dd<=td) else 0.0
    return min(1.0,j+subset_bonus)


def _avg_slot_evidence(ctx):
    slots=(ctx or {}).get('slots',{})
    vals=[float(slots.get(s,{}).get('evidence',0.0)) for s in SLOTS]
    return sum(vals)/4.0


@dataclass
class TransferDonorV57:
    donor_key:str
    similarity:float
    donor_evidence:float
    audit_multiplier:float
    audit_false_prune_rate:float
    edge_trust:float
    effective_weight:float
    disabled:bool
    reason:str


@dataclass
class UtilityPredictionV57:
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
    initial_slots:list[str]
    pruned_slots:list[str]
    reason:str
    def as_dict(self):return asdict(self)


class SimilarityTransferMemoryV57:
    def __init__(self,path=None):
        self.path=Path(path) if path else default_transfer_path_v57()
        self.edges={};self.generation=0;self._load()
    def _load(self):
        try:
            o=json.loads(self.path.read_text(encoding='utf-8'))
            if int(o.get('version',0))!=PROFILE_VERSION:return
            self.edges=dict(o.get('edges',{}));self.generation=max(0,int(o.get('generation',0)))
        except Exception:return
    def _payload(self):
        return {'version':PROFILE_VERSION,'generation':self.generation,'edges':self.edges,
                'privacy':'aggregate transfer calibration only; no audio/MIDI/score text/file names/identity'}
    def snapshot(self):return self._payload()
    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(self._payload(),sort_keys=True,indent=2)+'\n'
        fd,tmp=tempfile.mkstemp(prefix=self.path.name+'.',suffix='.tmp',dir=str(self.path.parent))
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            try:os.unlink(tmp)
            except FileNotFoundError:pass
    @staticmethod
    def edge_key(target,donor):return str(target)+'<-'+str(donor)
    def _edge(self,target,donor):
        return self.edges.setdefault(self.edge_key(target,donor),{
            'target':str(target),'donor':str(donor),'trust':1.0,'audits':0,'false_prunes':0,
            'clean_streak':0,'disabled':False,'recent':[],'max_false_prune_gain':0.0,
        })
    def calibration(self,target,donor):
        e=self._edge(target,donor)
        return {'trust':max(0.0,min(1.0,float(e.get('trust',1.0)))),
                'disabled':bool(e.get('disabled',False)),'audits':int(e.get('audits',0)),
                'false_prunes':int(e.get('false_prunes',0)),'clean_streak':int(e.get('clean_streak',0))}
    def record_audit(self,target,donors,audit_record):
        donors=list(dict.fromkeys(map(str,donors or [])))
        if not donors:return {'recorded':False,'reason':'no_transfer_donors'}
        false=bool((audit_record or {}).get('false_prune',False))
        gain=max(0.0,float((audit_record or {}).get('counterfactual_gain',0.0)))
        rows=[]
        for donor in donors:
            e=self._edge(target,donor);e['audits']=int(e.get('audits',0))+1
            recent=list(e.get('recent',[]))
            recent.append({'false_prune':false,'gain':round(gain,9)})
            e['recent']=recent[-8:]
            if false:
                e['false_prunes']=int(e.get('false_prunes',0))+1;e['clean_streak']=0
                # Strong but recoverable penalty on this transfer edge only.
                e['trust']=max(.15,float(e.get('trust',1.0))*(.56 if gain>=.05 else .66))
                e['max_false_prune_gain']=max(float(e.get('max_false_prune_gain',0.0)),gain)
            else:
                e['clean_streak']=int(e.get('clean_streak',0))+1
                e['trust']=min(1.0,float(e.get('trust',1.0))+.055)
            r4=e['recent'][-4:];fails=sum(1 for x in r4 if x.get('false_prune'))
            if (len(r4)>=4 and fails>=2) or float(e['trust'])<=EDGE_DISABLE_TRUST:
                e['disabled']=True
            if bool(e.get('disabled')) and int(e.get('clean_streak',0))>=EDGE_RECOVERY_CLEAN:
                e['disabled']=False;e['clean_streak']=0;e['trust']=max(.55,float(e.get('trust',0.0)))
                e['recent']=[x for x in e['recent'][-EDGE_RECOVERY_CLEAN:] if not x.get('false_prune')]
            rows.append({'donor':donor,**self.calibration(target,donor)})
        self.generation+=1;self._save()
        return {'recorded':True,'target':str(target),'false_prune':false,'gain':round(gain,9),
                'edges':rows,'generation':self.generation}


def collect_transfer_evidence_v57(target_key,utility_memory,audit_memory=None,transfer_memory=None):
    contexts=getattr(utility_memory,'contexts',{}) or {}
    target_char,target_dims=_parse_key(target_key)
    donors=[];slot_acc={s:{'w':0.0,'utility':0.0,'overall':0.0,'safety':0.0,'winrate':0.0,'evidence':0.0} for s in SLOTS}
    for donor_key,ctx in contexts.items():
        if str(donor_key)==str(target_key):continue
        sim=context_similarity_v57(target_key,donor_key)
        if sim<=0:continue
        donor_ev=_avg_slot_evidence(ctx)
        if donor_ev<MIN_DONOR_SLOT_EVIDENCE:continue
        audit_mult=1.0;rate=0.0;disabled=False
        if audit_memory is not None:
            cal=audit_memory.calibration(donor_key)
            disabled=bool(cal.get('disabled',False));rate=float(cal.get('recent_false_prune_rate',0.0))
            if disabled or (int(cal.get('recent_audits',0))>=3 and rate>=.20):
                donors.append(TransferDonorV57(str(donor_key),sim,donor_ev,float(cal.get('confidence_multiplier',1.0)),rate,0.0,0.0,True,'donor_audit_block'))
                continue
            audit_mult=max(.35,min(1.0,float(cal.get('confidence_multiplier',1.0))))
        edge_trust=1.0
        if transfer_memory is not None:
            ec=transfer_memory.calibration(target_key,donor_key)
            if ec['disabled']:
                donors.append(TransferDonorV57(str(donor_key),sim,donor_ev,audit_mult,rate,float(ec['trust']),0.0,True,'transfer_edge_disabled'))
                continue
            edge_trust=float(ec['trust'])
        weight=sim*audit_mult*edge_trust
        if weight<=.05:continue
        slots=(ctx or {}).get('slots',{})
        for s in SLOTS:
            rec=slots.get(s)
            if not rec:continue
            ev=float(rec.get('evidence',0.0))
            if ev<.5:continue
            eff_ev=min(MAX_TRANSFER_EVIDENCE_PER_SLOT,ev*weight*TRANSFER_EVIDENCE_SCALE)
            wr=float(rec.get('wins',0.0))/max(.5,ev)
            a=slot_acc[s];a['w']+=eff_ev;a['evidence']+=eff_ev
            a['utility']+=eff_ev*float(rec.get('utility',.5));a['overall']+=eff_ev*float(rec.get('overall',.5))
            a['safety']+=eff_ev*float(rec.get('safety',.5));a['winrate']+=eff_ev*wr
        donors.append(TransferDonorV57(str(donor_key),sim,donor_ev,audit_mult,rate,edge_trust,weight,False,'accepted'))
    synth={}
    for s,a in slot_acc.items():
        if a['w']<=0:continue
        synth[s]={'evidence':min(MAX_TRANSFER_EVIDENCE_PER_SLOT,a['evidence']),
                  'utility':a['utility']/a['w'],'overall':a['overall']/a['w'],
                  'safety':a['safety']/a['w'],'winrate':a['winrate']/a['w']}
    return synth,donors


def predict_candidate_utility_v57(character,dimensions,steered_scores=None,repair_reports=None,policy=None,
                                  utility_memory=None,audit_memory=None,transfer_memory=None,v54_primary=None):
    character=str(character);dims=[str(d) for d in (dimensions or []) if str(d) in CORE_DIMS]
    key=context_key_v55(character,dims)
    local=(utility_memory.context(key) if utility_memory else {}) or {};local_slots=local.get('slots',{})
    transfer,donor_rows=collect_transfer_evidence_v57(key,utility_memory,audit_memory,transfer_memory) if utility_memory else ({},[])
    steered_scores=steered_scores or {};repair_reports=repair_reports or {}
    structural_vals=[float(steered_scores.get(s,50.0)) for s in 'ABC']
    lo=min(structural_vals) if structural_vals else 0.;hi=max(structural_vals) if structural_vals else 1.;span=max(1.0,hi-lo)
    scores={}
    for s in SLOTS:
        u=float(CHAR_PRIOR.get(character,CHAR_PRIOR['sustain'])[s])
        for d in dims:u+=DIM_PRIOR.get(d,{}).get(s,0.0)/max(1,len(dims))
        if s in 'ABC':
            u+=.10*((float(steered_scores.get(s,lo))-lo)/span-.5)
            rep=repair_reports.get(s)
            if rep is not None:u+=.0015*max(-20.0,min(30.0,float(getattr(rep,'improvement',0.0))))
        u+=_policy_bias(s,policy)
        lr=local_slots.get(s);tr=transfer.get(s)
        lev=float((lr or {}).get('evidence',0.0));tev=float((tr or {}).get('evidence',0.0))
        if lr or tr:
            lw=max(0.0,lev);tw=max(0.0,tev*.55) # transferred evidence is always discounted again at read time
            den=max(.001,lw+tw)
            if lr:
                lwr=float(lr.get('wins',0.0))/max(.5,lev);lh=.70*float(lr.get('utility',.5))+.30*lwr
            else:lh=.5
            th=.70*float((tr or {}).get('utility',.5))+.30*float((tr or {}).get('winrate',.0)) if tr else .5
            hist=(lw*lh+tw*th)/den
            trust=min(.55,.10*lev+.055*tev)
            u=(1-trust)*u+trust*hist
        scores[s]=_clip(u)
    ranking=sorted(SLOTS,key=lambda s:(scores[s],s=='D'),reverse=True)
    pred_margin=float(scores[ranking[0]]-scores[ranking[1]])
    local_evs=[float(local_slots.get(s,{}).get('evidence',0.0)) for s in SLOTS]
    transfer_evs=[float(transfer.get(s,{}).get('evidence',0.0)) for s in SLOTS]
    local_ev=sum(local_evs)/4.0;transfer_ev=sum(transfer_evs)/4.0
    effective_ev=local_ev+.55*transfer_ev
    completeness=sum(1 for le,te in zip(local_evs,transfer_evs) if le+te*.55>=2.0)/4.0
    confidence=_clip(.18+min(.52,effective_ev*.07)+.22*completeness+min(.16,pred_margin*.8))
    # Safety cap: transfer alone can accelerate to Top2+D, never Top1+D.
    if local_ev<.5:confidence=min(confidence,TRANSFER_CONF_CAP_NO_LOCAL)
    elif local_ev<HIGH_LOCAL_EVIDENCE_FLOOR:confidence=min(confidence,.71)
    transfer_conf=_clip(min(1.0,transfer_ev/3.0)*(sum(r.effective_weight for r in donor_rows if not r.disabled)/max(1,sum(1 for r in donor_rows if not r.disabled)))) if donor_rows else 0.0
    non_d=[s for s in ranking if s!='D'];primary=list(v54_primary or SLOTS)
    if local_ev>=HIGH_LOCAL_EVIDENCE_FLOOR and confidence>=HIGH_CONF and pred_margin>=HIGH_PRED_MARGIN and effective_ev>=3.0:
        initial=[non_d[0],'D'];reason='hybrid_high_conf_top1_plus_D'
    elif confidence>=MED_CONF and effective_ev>=1.5:
        initial=[non_d[0],non_d[1],'D'];reason='similarity_transfer_top2_plus_D' if transfer_ev>local_ev else 'local_top2_plus_D'
    else:
        initial=list(primary);reason='v54_primary_fallback'
    initial=list(dict.fromkeys(initial));
    if 'D' not in initial:initial.append('D')
    pruned=[s for s in SLOTS if s not in initial]
    accepted=[r.donor_key for r in donor_rows if not r.disabled and r.effective_weight>0]
    return UtilityPredictionV57(
        key,character,sorted(set(dims)),{k:round(v,6) for k,v in scores.items()},ranking,
        round(confidence,6),round(pred_margin,6),round(effective_ev,6),round(local_ev,6),round(transfer_ev,6),
        round(transfer_conf,6),accepted,[asdict(r) for r in donor_rows],initial,pruned,reason
    )
