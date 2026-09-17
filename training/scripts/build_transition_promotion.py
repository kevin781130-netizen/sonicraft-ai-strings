#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from transition_promotion import build_transition_promotion

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline',required=True);ap.add_argument('--candidate',required=True);ap.add_argument('--curriculum',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--min-samples',type=int,default=48);ap.add_argument('--max-continuity-ratio',type=float,default=.99)
    ap.add_argument('--max-accel-ratio',type=float,default=1.02);ap.add_argument('--max-flow-ratio',type=float,default=1.03);ap.add_argument('--max-composite-ratio',type=float,default=.995)
    a=ap.parse_args();r=build_transition_promotion(load(a.baseline),load(a.candidate),load(a.curriculum),min_samples=a.min_samples,
        max_continuity_ratio=a.max_continuity_ratio,max_accel_ratio=a.max_accel_ratio,max_flow_ratio=a.max_flow_ratio,max_composite_ratio=a.max_composite_ratio)
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(r,indent=2,sort_keys=True))
    if not r['promotion_pass']: raise SystemExit(2)

if __name__=='__main__':main()
