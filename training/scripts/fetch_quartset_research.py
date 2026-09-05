from __future__ import annotations
import argparse, json, zipfile
from pathlib import Path
import requests

RECORD='15708701'
API=f'https://zenodo.org/api/records/{RECORD}'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='datasets/research/QuartSet'); a=ap.parse_args()
    root=Path(a.out); root.mkdir(parents=True,exist_ok=True)
    print('*** RESEARCH-ONLY GATE ***')
    print('QuartSet is free to access, but this project has not verified an explicit commercial-training grant.')
    print('Any checkpoint trained with this source must remain release_blocked=true until rights are cleared.')
    meta=requests.get(API,timeout=60).json()
    (root/'zenodo_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    files=meta.get('files',[])
    targets=[f for f in files if f.get('key','').lower().endswith('.zip')]
    if not targets: raise RuntimeError('No ZIP found in current QuartSet Zenodo record.')
    for f in targets:
        url=f.get('links',{}).get('content') or f.get('links',{}).get('self')
        dest=root/f['key']
        if not dest.exists():
            with requests.get(url,stream=True,timeout=120) as r:
                r.raise_for_status()
                with dest.open('wb') as o:
                    for chunk in r.iter_content(1024*1024):
                        if chunk:o.write(chunk)
        ex=root/dest.stem
        if not (ex/'.extracted').exists():
            ex.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(dest) as z:z.extractall(ex)
            (ex/'.extracted').write_text('release_blocked=true\n',encoding='utf-8')
    (root/'RELEASE_BLOCKED.txt').write_text(
        'This dataset is enabled for research experiments only. Do not ship a model trained on it until an explicit commercial training/model-distribution grant is verified.\n',encoding='utf-8')
if __name__=='__main__':main()
