from __future__ import annotations
"""Small dependency-free ABX trial builder/scorer for codec transparency checks."""
from pathlib import Path
from typing import Sequence,Mapping
import hashlib,json,math,random,shutil

ABX_SCHEMA=1

def _token(seed:int,trial:int,label:str)->str:
    return hashlib.sha256(f'{seed}:{trial}:{label}'.encode()).hexdigest()[:16]

def build_trials(pairs:Sequence[Mapping],out_dir:str|Path,*,seed:int=1909)->tuple[dict,dict]:
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); rng=random.Random(seed); public=[];answers=[]
    for i,row in enumerate(pairs):
        ref=Path(row['reference']); cand=Path(row['reconstruction']); truth=rng.choice(('A','B'))
        # A/B ordering is randomized independently of X identity.
        ref_is_a=rng.choice((True,False)); A=ref if ref_is_a else cand; B=cand if ref_is_a else ref
        x_source=A if truth=='A' else B
        tid=_token(seed,i,'trial'); paths={}
        for label,src in (('A',A),('B',B),('X',x_source)):
            ext=src.suffix.lower() or '.wav'; dst=out/f'{tid}_{label}{ext}'; shutil.copy2(src,dst); paths[label]=dst.name
        public.append({'trial_id':tid,'A':paths['A'],'B':paths['B'],'X':paths['X'],'candidate_id':row.get('candidate_id')})
        answers.append({'trial_id':tid,'answer':truth,'ref_is_A':ref_is_a,'candidate_id':row.get('candidate_id')})
    return {'schema':ABX_SCHEMA,'seed_commitment':hashlib.sha256(str(seed).encode()).hexdigest(),'trials':public}, {'schema':ABX_SCHEMA,'answers':answers}

def exact_binomial_upper(k:int,n:int,p:float=.5)->float:
    if n<=0:return 1.0
    return float(sum(math.comb(n,i)*(p**i)*((1-p)**(n-i)) for i in range(k,n+1)))

def score_responses(answer_key:Mapping,responses:Sequence[Mapping],*,target_max_accuracy:float=.60)->dict:
    key={x['trial_id']:x['answer'] for x in answer_key.get('answers',[])}; by_listener={};correct=0;total=0
    for r in responses:
        tid=str(r.get('trial_id')); guess=str(r.get('answer') or r.get('guess') or '').upper(); lid=str(r.get('listener_id') or 'anonymous')
        if tid not in key or guess not in ('A','B'):continue
        ok=guess==key[tid];correct+=int(ok);total+=1; e=by_listener.setdefault(lid,[0,0]);e[0]+=int(ok);e[1]+=1
    acc=correct/total if total else None; pval=exact_binomial_upper(correct,total,.5) if total else 1.0
    return {'schema':ABX_SCHEMA,'listener_count':len(by_listener),'trial_count':total,'correct':correct,'accuracy':acc,
            'chance_upper_p':pval,'target_max_accuracy':target_max_accuracy,
            'transparency_pass':bool(acc is not None and acc<=target_max_accuracy),
            'by_listener':{k:{'correct':v[0],'trials':v[1],'accuracy':v[0]/v[1]} for k,v in by_listener.items() if v[1]}}
