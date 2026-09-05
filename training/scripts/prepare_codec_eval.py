from __future__ import annotations
import argparse,json,shutil
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--forge-manifest',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--max-clips',type=int,default=64);a=ap.parse_args()
    rows=[json.loads(x) for x in Path(a.forge_manifest).read_text().splitlines() if x.strip()]
    rows=[r for r in rows if r.get('forge_release_eligible') and str(r.get('training_origin','real')).lower()=='real']
    # Deterministic quality-first ordering with source/cell interleaving key.
    rows.sort(key=lambda r:(-float(r.get('forge_quality_score',0)),str(r.get('dataset') or r.get('dataset_id')),str(r.get('forge_sha256') or '')))
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);refs=[]
    for i,r in enumerate(rows[:a.max_clips]):
        src=Path(r.get('audio') or r.get('path') or r.get('file'));ext=src.suffix.lower() if src.suffix else '.wav';dst=out/f'{i:04d}{ext}';shutil.copy2(src,dst)
        refs.append({'eval_id':f'{i:04d}','reference':str(dst.resolve()),'filename':dst.name,'dataset':r.get('dataset') or r.get('dataset_id'),'training_origin':'real',
                     'instrument':r.get('instrument'), 'articulation':r.get('articulation'),'forge_quality_score':r.get('forge_quality_score')})
    (out/'codec_eval_refs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in refs),encoding='utf-8');print('prepared',len(refs),'real codec references ->',out)
    if not refs:raise SystemExit(2)
if __name__=='__main__':main()
