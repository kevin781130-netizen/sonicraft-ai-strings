from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def group_key(r):
    # Prefer piece/session/player identifiers to prevent adjacent clips from leaking across splits.
    return str(r.get('session_id') or r.get('piece_id') or r.get('source_file') or r.get('performer_id') or r.get('file'))

def bucket(key):
    return int(hashlib.sha1(key.encode('utf-8')).hexdigest()[:8],16)%100

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--index',required=True); ap.add_argument('--train',required=True); ap.add_argument('--val',required=True); ap.add_argument('--val-percent',type=int,default=8); a=ap.parse_args()
    rows=[json.loads(x) for x in Path(a.index).read_text(encoding='utf-8').splitlines() if x.strip()]
    tr=[]; va=[]
    for r in rows: (va if bucket(group_key(r))<a.val_percent else tr).append(r)
    if not va and len(rows)>1: va=[tr.pop()]
    for path,data in [(a.train,tr),(a.val,va)]:
        p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in data),encoding='utf-8')
    print('train',len(tr),'val',len(va),'group-safe split')
if __name__=='__main__': main()
