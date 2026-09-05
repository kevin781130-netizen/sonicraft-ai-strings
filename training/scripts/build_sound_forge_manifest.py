from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sound_forge import build_forge, read_jsonl, write_jsonl


def main():
    ap=argparse.ArgumentParser(description='SONICRAFT v1.9 fail-closed real/modeled string dataset forge')
    ap.add_argument('--input',action='append',required=True,help='Input JSONL manifest(s)')
    ap.add_argument('--registry',default=str(ROOT/'dataset_registry.json'))
    ap.add_argument('--out',required=True,help='Eligible forged JSONL')
    ap.add_argument('--report',required=True)
    ap.add_argument('--rejected',default=None)
    ap.add_argument('--no-hash',action='store_true',help='Development-only speed option; release forge should keep hashes')
    ap.add_argument('--allow-fail',action='store_true',help='Research audit only; production exits nonzero when report release_pass=false')
    ap.add_argument('--curriculum',default='lane_locked_quality_coverage_forge_v19',choices=('lane_locked_quality_coverage_forge_v19','lane_locked_acoustic_promotion_v20'))
    a=ap.parse_args()
    rows=[]
    for p in a.input: rows.extend(read_jsonl(p))
    registry=json.loads(Path(a.registry).read_text(encoding='utf-8'))
    forged,report=build_forge(rows,registry,hash_audio=not a.no_hash,curriculum=a.curriculum)
    write_jsonl(a.out,[r for r in forged if r.get('forge_release_eligible')])
    if a.rejected: write_jsonl(a.rejected,[r for r in forged if not r.get('forge_release_eligible')])
    rp=Path(a.report); rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('release_pass','input_files','eligible_files','eligible_real_files','eligible_modeled_files','rejected_files','duplicate_audio','rights_failures','audio_failures')},indent=2))
    if not report['release_pass'] and not a.allow_fail: raise SystemExit(2)

if __name__=='__main__': main()
