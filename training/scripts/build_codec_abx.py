from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from codec_tournament import load_pairs
from blind_abx import build_trials

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--pairs',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--seed',type=int,default=1909);a=ap.parse_args()
    pub,key=build_trials(load_pairs(a.pairs),a.out_dir,seed=a.seed);od=Path(a.out_dir)
    (od/'abx_trials.json').write_text(json.dumps(pub,indent=2),encoding='utf-8');(od/'abx_answer_key.private.json').write_text(json.dumps(key,indent=2),encoding='utf-8')
    print('WROTE',len(pub['trials']),'ABX trials to',od)
if __name__=='__main__':main()
