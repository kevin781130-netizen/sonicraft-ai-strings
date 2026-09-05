from __future__ import annotations
import argparse, json, hashlib, urllib.request, zipfile
from pathlib import Path
RECORD='8147435'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='datasets/raw/ghent_ar_violin_2023');a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    meta=json.load(urllib.request.urlopen(f'https://zenodo.org/api/records/{RECORD}'))
    files=meta.get('files',[]); target=next((f for f in files if f.get('key')=='Avatar_Data.zip'),None)
    if not target: raise RuntimeError('Avatar_Data.zip not found in Zenodo record')
    url=(target.get('links') or {}).get('self') or (target.get('links') or {}).get('content')
    zpath=out/'Avatar_Data.zip'; urllib.request.urlretrieve(url,zpath)
    print('downloaded',zpath,hashlib.sha256(zpath.read_bytes()).hexdigest())
    with zipfile.ZipFile(zpath) as z:z.extractall(out/'avatar')
    # Only professional avatar leader audio is admitted by default.
    rows=[]
    for p in sorted((out/'avatar').rglob('*_Audio.wav')):
        if p.name.startswith(('First_Violin_','Second_Violin_')):
            rows.append({'audio':str(p.resolve()),'dataset':'ghent_ar_violin_2023','instrument':'violin','role':'professional_avatar_section_leader','license':'CC-BY-4.0','release_blocked':False})
    mf=out/'manifest.jsonl';mf.write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8');print('manifest',mf,'rows',len(rows))
if __name__=='__main__': main()
