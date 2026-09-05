from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blind_abx import score_responses

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--key',required=True);ap.add_argument('--responses',required=True);ap.add_argument('--out',required=True);ap.add_argument('--target-max-accuracy',type=float,default=.60);a=ap.parse_args()
    key=json.loads(Path(a.key).read_text());p=Path(a.responses); rows=[]
    if p.suffix.lower()=='.csv':
        with p.open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    else:
        rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    report=score_responses(key,rows,target_max_accuracy=a.target_max_accuracy);Path(a.out).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
