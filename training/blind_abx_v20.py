from __future__ import annotations
"""Commercial ABX scorer with listener QA and statistical guardrails.

The scorer accepts both the current ``answers`` key shape and the legacy
``trials/generated_side`` shape emitted by older SONICRAFT blind-test packets.
Responses may use ``answer``, ``guess`` or the historical ``pick_generated``
column. This keeps old evidence readable while giving new packets one v20 path.
"""
from typing import Mapping,Sequence
import math

ABX_SCHEMA=2


def exact_binomial_upper(k:int,n:int,p=.5):
    if n<=0:return 1.0
    return float(sum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1)))


def wilson(k:int,n:int,z=1.959963984540054):
    if n<=0:return (0.0,1.0)
    ph=k/n;d=1+z*z/n;c=(ph+z*z/(2*n))/d;h=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)


def normalize_answer_key(answer_key:Mapping)->dict[str,dict]:
    """Return a trial-id keyed v20 view of current or legacy answer keys."""
    raw=answer_key.get('answers')
    if raw is None:
        raw=answer_key.get('trials',[])
    out={}
    for item in raw or []:
        if not isinstance(item,Mapping):continue
        tid=str(item.get('trial_id') or '').strip()
        answer=str(item.get('answer') or item.get('generated_side') or '').upper().strip()
        if not tid or answer not in ('A','B'):continue
        kind=str(item.get('trial_kind') or 'target').lower().strip() or 'target'
        out[tid]={'trial_id':tid,'answer':answer,'trial_kind':kind}
    return out


def score_abx_v20(answer_key:Mapping,responses:Sequence[Mapping],*,target_max_accuracy=.60,min_listener_trials=8,min_listeners=5,min_total_trials=60,
                   qa_min_accuracy=.75,alpha=.05):
    key=normalize_answer_key(answer_key);stats={}
    for r in responses:
        tid=str(r.get('trial_id') or '').strip()
        guess=str(r.get('answer') or r.get('guess') or r.get('pick_generated') or '').upper().strip()
        lid=str(r.get('listener_id') or r.get('participant_id') or 'anonymous').strip() or 'anonymous'
        if tid not in key or guess not in ('A','B'):continue
        truth=str(key[tid].get('answer','')).upper();kind=str(key[tid].get('trial_kind','target')).lower()
        if truth not in ('A','B'):continue
        e=stats.setdefault(lid,{'target':[0,0],'qa':[0,0]});slot='qa' if kind in ('qa','attention','gold') else 'target';e[slot][0]+=int(guess==truth);e[slot][1]+=1
    accepted={};excluded={}
    for lid,s in stats.items():
        tc,tn=s['target'];qc,qn=s['qa'];qa_acc=qc/qn if qn else 1.0
        if tn<min_listener_trials:excluded[lid]='insufficient_target_trials'
        elif qn and qa_acc<qa_min_accuracy:excluded[lid]='failed_attention_trials'
        else:accepted[lid]=s
    correct=sum(v['target'][0] for v in accepted.values());total=sum(v['target'][1] for v in accepted.values());acc=correct/total if total else None
    lo,hi=wilson(correct,total);p_above=exact_binomial_upper(correct,total,.5) if total else 1.0
    significant_above_chance=bool(total and acc>.5 and p_above<alpha)
    pass_=bool(len(accepted)>=min_listeners and total>=min_total_trials and acc is not None and acc<=target_max_accuracy and not significant_above_chance)
    return {'schema':ABX_SCHEMA,'listener_count':len(accepted),'excluded_listener_count':len(excluded),'trial_count':total,'correct':correct,'accuracy':acc,
            'wilson95_low':lo,'wilson95_high':hi,'chance_upper_p':p_above,'significant_above_chance':significant_above_chance,'alpha':alpha,
            'target_max_accuracy':target_max_accuracy,'min_listeners':min_listeners,'min_total_trials':min_total_trials,'min_listener_trials':min_listener_trials,
            'qa_min_accuracy':qa_min_accuracy,'transparency_pass':pass_,'by_listener':{k:{'target_correct':v['target'][0],'target_trials':v['target'][1],
            'target_accuracy':v['target'][0]/v['target'][1] if v['target'][1] else None,'qa_correct':v['qa'][0],'qa_trials':v['qa'][1],
            'qa_accuracy':v['qa'][0]/v['qa'][1] if v['qa'][1] else None} for k,v in accepted.items()},'excluded':excluded}
