from __future__ import annotations
import argparse, json, tarfile, zipfile
from pathlib import Path
import requests

RECORD_ID="3685367"
API=f"https://zenodo.org/api/records/{RECORD_ID}"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='datasets/raw/TinySOL'); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    meta=requests.get(API,timeout=60); meta.raise_for_status(); rec=meta.json()
    (out/'zenodo_record.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
    for f in rec.get('files',[]):
        name=f['key']; url=f.get('links',{}).get('self') or f.get('links',{}).get('download')
        if not url: continue
        dest=out/name
        if not dest.exists():
            print('download',name)
            with requests.get(url,stream=True,timeout=120) as r:
                r.raise_for_status()
                with open(dest,'wb') as w:
                    for chunk in r.iter_content(1024*1024):
                        if chunk: w.write(chunk)
        try:
            if dest.suffix=='.zip': zipfile.ZipFile(dest).extractall(out/'extracted')
            elif dest.name.endswith(('.tar.gz','.tgz')): tarfile.open(dest,'r:gz').extractall(out/'extracted')
        except Exception as e: print('extract skipped:',dest,e)
    print('TinySOL ready:',out)

if __name__=='__main__': main()
