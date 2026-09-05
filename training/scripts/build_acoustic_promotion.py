from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
from acoustic_promotion import build_promotion

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sound-forge',required=True);ap.add_argument('--segments',required=True);ap.add_argument('--codec-tournament',required=True);ap.add_argument('--codec-abx',required=True);ap.add_argument('--generated-real-abx',required=True);ap.add_argument('--shipping-codec',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    r=build_promotion(load(a.sound_forge),load(a.segments),load(a.codec_tournament),load(a.codec_abx),load(a.generated_real_abx),shipping_codec=a.shipping_codec);Path(a.out).write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(0 if r['promotion_pass'] else 2)
if __name__=='__main__':main()
