from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blind_abx_v20 import score_abx_v20

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--key',required=True);ap.add_argument('--responses',required=True);ap.add_argument('--out',required=True);ap.add_argument('--target-max-accuracy',type=float,default=.60);ap.add_argument('--min-listeners',type=int,default=5);ap.add_argument('--min-total-trials',type=int,default=60);a=ap.parse_args()
    key=json.loads(Path(a.key).read_text());p=Path(a.responses);rows=[]
    if p.suffix.lower()=='.csv':
        with p.open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    else:rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    r=score_abx_v20(key,rows,target_max_accuracy=a.target_max_accuracy,min_listeners=a.min_listeners,min_total_trials=a.min_total_trials);Path(a.out).write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(0 if r['transparency_pass'] else 2)
if __name__=='__main__':main()
