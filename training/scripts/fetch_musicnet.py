from __future__ import annotations
import argparse,json,hashlib,tarfile,urllib.request
from pathlib import Path
RECORD='5120004'; API=f'https://zenodo.org/api/records/{RECORD}'

def stream(url,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(url) as r, open(dst,'wb') as f:
        while True:
            b=r.read(8*1024*1024)
            if not b: break
            f.write(b)
    return dst

def main():
    ap=argparse.ArgumentParser(description='Optional MusicNet downloader. Full audio is ~11.1GB; keep this outside the small core.')
    ap.add_argument('--out',default='datasets/raw/musicnet');ap.add_argument('--full',action='store_true');a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    meta=json.load(urllib.request.urlopen(API));files={f['key']:f for f in meta.get('files',[])}
    names=['musicnet_metadata.csv'] + (['musicnet_midis.tar.gz','musicnet.tar.gz'] if a.full else [])
    for name in names:
        f=files.get(name)
        if not f: raise RuntimeError(f'{name} missing from Zenodo record')
        url=(f.get('links') or {}).get('self') or (f.get('links') or {}).get('content');dst=out/name
        if not dst.exists() or dst.stat().st_size!=int(f.get('size') or dst.stat().st_size):
            print('downloading',name,'size',f.get('size'));stream(url,dst)
        checksum=str(f.get('checksum') or '')
        if checksum.startswith('md5:'):
            got=hashlib.md5(dst.read_bytes()).hexdigest() if dst.stat().st_size<300_000_000 else None
            if got and got!=checksum.split(':',1)[1]:raise RuntimeError(f'MD5 mismatch {name}')
    (out/'SOURCE_PROVENANCE.txt').write_text('dataset=MusicNet\ndoi=10.5281/zenodo.5120004\nrecord=330 freely licensed classical recordings\nindex=OpenAIRE CC BY\nretain_track_source_provenance=true\n',encoding='utf-8')
    if a.full:
        for name in ('musicnet_midis.tar.gz','musicnet.tar.gz'):
            dst=out/name;target=out/name.replace('.tar.gz','')
            if not target.exists():
                target.mkdir(parents=True,exist_ok=True);print('extracting',name);tarfile.open(dst,'r:gz').extractall(target)
    print('Done:',out,'FULL' if a.full else 'metadata only')
if __name__=='__main__':main()
