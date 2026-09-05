from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
from acoustic_segmentation import segment_forged_rows,write_jsonl

def load_jsonl(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--forge-manifest',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--out-manifest',required=True);ap.add_argument('--report',required=True)
    ap.add_argument('--min-sec',type=float,default=1.5);ap.add_argument('--target-sec',type=float,default=6.0);ap.add_argument('--max-sec',type=float,default=10.0);a=ap.parse_args()
    rows=load_jsonl(a.forge_manifest);segs,rep=segment_forged_rows(rows,a.out_dir,min_sec=a.min_sec,target_sec=a.target_sec,max_sec=a.max_sec);write_jsonl(segs,a.out_manifest);Path(a.report).write_text(json.dumps(rep,indent=2),encoding='utf-8');print(json.dumps(rep,indent=2))
if __name__=='__main__':main()
