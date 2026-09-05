from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from codec_tournament import load_pairs,run_tournament

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--pairs',required=True); ap.add_argument('--out',required=True)
    ap.add_argument('--min-quality',type=float,default=80.0); ap.add_argument('--tie-window',type=float,default=.50)
    ap.add_argument('--allow-fail',action='store_true'); a=ap.parse_args()
    r=run_tournament(load_pairs(a.pairs),min_quality=a.min_quality,tie_window=a.tie_window)
    p=Path(a.out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(r,indent=2),encoding='utf-8')
    print(json.dumps({k:r.get(k) for k in ('promotion_pass','winner','winner_kind','winner_quality','real_anchor_count')},indent=2))
    if not r.get('promotion_pass') and not a.allow_fail: raise SystemExit(2)
if __name__=='__main__':main()
