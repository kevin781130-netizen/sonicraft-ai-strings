from __future__ import annotations
import argparse, json, re
from pathlib import Path

CODES={'vn':'violin','va':'viola','vc':'cello'}
PAT=re.compile(r'^AuSep_(\d+)_(vn|va|vc)_(\d+)_(.+)\.wav$',re.I)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='datasets/raw/URMP'); ap.add_argument('--out',default='datasets/manifests/urmp_strings.jsonl'); a=ap.parse_args()
    root=Path(a.root); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for wav in root.rglob('AuSep_*.wav'):
        m=PAT.match(wav.name)
        if not m: continue
        track,code,piece,title=m.groups(); code=code.lower()
        ann=wav.with_name(f'Notes_{track}_{code}_{piece}_{title}.txt')
        if not ann.exists():
            print('missing annotation',wav); continue
        rows.append({'dataset':'urmp','audio':str(wav.resolve()),'notes':str(ann.resolve()),'instrument':CODES[code],
                     'instrument_code':code,'piece_id':piece,'title':title,'license':'VERIFY_BEFORE_COMMERCIAL_RELEASE','release_blocked':True})
    with open(out,'w',encoding='utf-8') as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print(f'wrote {len(rows)} string stems -> {out}')

if __name__=='__main__': main()
