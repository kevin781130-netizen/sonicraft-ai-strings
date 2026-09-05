from __future__ import annotations
import argparse,json,hashlib,re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_policy import load_registry, assert_commercial_sources

PER_FILE={'musicnet_audited','wikimedia_pd_quartets','fsd50k_cc0_strings','open_music_archive_pd'}
SAFE_PATTERNS=('cc0','public domain','cc-by','cc by','creative commons attribution')

def safe_license(s):
    x=re.sub(r'\s+',' ',str(s or '').strip().lower())
    if any(bad in x for bad in ('noncommercial','non-commercial','cc-by-nc','cc by-nc','cc-by-sa','cc by-sa')): return False
    return any(ok in x for ok in SAFE_PATTERNS) or x in {'pd','public-domain'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--out',required=True);ap.add_argument('--registry',default='training/dataset_registry.json');a=ap.parse_args()
    reg=load_registry(a.registry);rows=[];errs=[]
    for i,line in enumerate(Path(a.manifest).read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():continue
        r=json.loads(line);sid=str(r.get('dataset') or r.get('dataset_id') or '')
        try:assert_commercial_sources([sid],a.registry)
        except Exception as e:errs.append(f'line {i}: {e}');continue
        p=Path(r.get('audio') or '')
        if not p.exists():errs.append(f'line {i}: missing audio {p}');continue
        if sid in PER_FILE:
            if not safe_license(r.get('license')):errs.append(f'line {i}: per-file license not safely whitelisted: {r.get("license")}');continue
            if not (r.get('source_url') or r.get('provenance_url') or r.get('source_record')):errs.append(f'line {i}: per-file source URL/provenance required');continue
        rr=dict(r);rr['audio_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();rr['release_blocked']=False;rows.append(rr)
    if errs:
        print('\n'.join('[BLOCK] '+x for x in errs),file=sys.stderr);raise SystemExit(2)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8')
    print('audited',len(rows),'commercial real recordings ->',out)
if __name__=='__main__':main()
