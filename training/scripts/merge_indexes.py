#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--index',action='append',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    rows=[]; seen=set()
    for src in a.index:
        for line in Path(src).read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            r=json.loads(line); key=str(r.get('file') or r.get('audio') or r.get('path'))
            if key and key in seen: continue
            if key: seen.add(key)
            rows.append(r)
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    print('merged',len(rows),'rows ->',out)
if __name__=='__main__': main()
