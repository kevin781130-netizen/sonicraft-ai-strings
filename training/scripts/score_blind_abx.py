from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path

def wilson(k,n,z=1.96):
    if not n:return (0,1)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return max(0,c-h),min(1,c+h)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--responses',required=True); ap.add_argument('--answer-key',required=True); ap.add_argument('--out',required=True); ap.add_argument('--threshold',type=float,default=.60); ap.add_argument('--min-trials',type=int,default=20); a=ap.parse_args()
    key=json.loads(Path(a.answer_key).read_text(encoding='utf-8')); ans={x['trial_id']:x['generated_side'] for x in key['trials']}
    rows=list(csv.DictReader(Path(a.responses).open(encoding='utf-8-sig'))); valid=[]
    for r in rows:
        pick=(r.get('pick_generated') or '').strip().upper()
        if r.get('trial_id') in ans and pick in ('A','B'): valid.append((r['trial_id'],pick))
    if len(valid)<a.min_trials: raise SystemExit(f'need >= {a.min_trials} completed blind trials; found {len(valid)}')
    correct=sum(p==ans[t] for t,p in valid); acc=correct/len(valid); lo,hi=wilson(correct,len(valid))
    passed=acc<=a.threshold
    out={'schema':1,'completed_trials':len(valid),'correct_generated_identifications':correct,'generated_identification_accuracy':acc,'wilson95_low':lo,'wilson95_high':hi,'pass_threshold':a.threshold,'abx_pass':passed,
         'interpretation':'Lower identification accuracy is better for realism; 0.50 is chance in this paired test.'}
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(out,indent=2)); raise SystemExit(0 if passed else 3)
if __name__=='__main__': main()
