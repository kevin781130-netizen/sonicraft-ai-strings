from __future__ import annotations
import argparse,json,re
from pathlib import Path

def guess_instrument(path:str):
    s=path.lower()
    if 'violin' in s: return 'violin'
    if 'viola' in s: return 'viola'
    if 'violoncello' in s or 'cello' in s: return 'cello'
    if 'contrabass' in s or 'double_bass' in s: return 'bass'
    return None

def guess_dynamic(path:str):
    s=Path(path).name.lower()
    for d in ('ppp','pp','mp','mf','ff','fff','p','f'):
        if re.search(rf'(^|[._ -]){d}([._ -]|$)',s): return d
    return 'unknown'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='datasets/raw/TinySOL'); ap.add_argument('--out',default='datasets/manifests/tinysol_strings.jsonl'); a=ap.parse_args()
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); rows=[]
    for p in Path(a.root).rglob('*.wav'):
        ins=guess_instrument(str(p))
        if ins in {'violin','viola','cello'}:
            rows.append({'dataset':'tinysol','audio':str(p.resolve()),'instrument':ins,'dynamic':guess_dynamic(str(p)),'license':'CC-BY-4.0','release_blocked':False})
    with open(out,'w',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print('wrote',len(rows),out)
if __name__=='__main__':main()
