from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from codec_tournament import load_pairs
from codec_tournament_v20 import run_tournament_v20

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--pairs',required=True);ap.add_argument('--out',required=True);ap.add_argument('--min-quality',type=float,default=82.0);ap.add_argument('--tie-window',type=float,default=.40);ap.add_argument('--min-real-anchors',type=int,default=8);ap.add_argument('--allow-fail',action='store_true');a=ap.parse_args()
    r=run_tournament_v20(load_pairs(a.pairs),min_quality=a.min_quality,tie_window=a.tie_window,min_real_anchors=a.min_real_anchors);Path(a.out).write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:r.get(k) for k in ('promotion_pass','winner','winner_kind','winner_quality','real_anchor_count')},indent=2));
    if not r.get('promotion_pass') and not a.allow_fail:raise SystemExit(2)
if __name__=='__main__':main()
