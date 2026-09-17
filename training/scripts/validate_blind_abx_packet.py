#!/usr/bin/env python3
from __future__ import annotations
"""Validate a prepared blind ABX packet before it is distributed to listeners.

This is a packaging/integrity check, not an acoustic quality judgment. It verifies
that public trial files match the private answer-key hashes and that answer-bearing
fields have not leaked into the public response template.
"""
import argparse,csv,hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from blind_abx_v20 import normalize_answer_key

AUDIO_EXT={'.wav','.flac','.aif','.aiff'}
FORBIDDEN_PUBLIC_FIELDS={'answer','generated_side','truth','is_generated','source_stem','trial_kind'}


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def fail(message:str)->None:
    raise SystemExit('ABX PACKET FAIL: '+message)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--packet',required=True)
    ap.add_argument('--min-trials',type=int,default=20)
    ap.add_argument('--out')
    a=ap.parse_args();packet=Path(a.packet);pub=packet/'public';prv=packet/'private'
    if not pub.is_dir():fail('public directory missing')
    if not prv.is_dir():fail('private directory missing')
    key_path=prv/'answer_key.json';responses_path=pub/'responses.csv'
    if not key_path.is_file():fail('private/answer_key.json missing')
    if not responses_path.is_file():fail('public/responses.csv missing')
    if (pub/'answer_key.json').exists():fail('answer key leaked into public directory')

    try:key_raw=json.loads(key_path.read_text(encoding='utf-8'))
    except Exception as e:fail('invalid answer key JSON: '+str(e))
    key=normalize_answer_key(key_raw)
    if len(key)<a.min_trials:fail(f'need >= {a.min_trials} valid target/QA answers; found {len(key)}')
    if len(key)!=len(set(key)):fail('duplicate trial IDs in answer key')

    detailed={}
    for item in list(key_raw.get('answers') or [])+list(key_raw.get('trials') or []):
        if isinstance(item,dict) and item.get('trial_id') and str(item['trial_id']) not in detailed:
            detailed[str(item['trial_id'])]=item

    with responses_path.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f);fields=list(reader.fieldnames or []);rows=list(reader)
    required={'listener_id','trial_id','A_file','B_file','pick_generated'}
    missing=sorted(required-set(fields))
    if missing:fail('public response template missing fields: '+', '.join(missing))
    leaked=sorted(FORBIDDEN_PUBLIC_FIELDS & set(fields))
    if leaked:fail('answer-bearing fields leaked into public response template: '+', '.join(leaked))
    row_ids=[str(r.get('trial_id') or '').strip() for r in rows]
    if len(row_ids)!=len(set(row_ids)):fail('duplicate trial IDs in public response template')
    if set(row_ids)!=set(key):fail('public response trial IDs do not exactly match private key')

    checked_audio=0
    for row in rows:
        tid=str(row['trial_id']).strip();detail=detailed.get(tid,{})
        for side in ('A','B'):
            name=str(row.get(side+'_file') or '').strip()
            if not name or Path(name).name!=name:fail(f'{tid} {side}_file must be a basename')
            path=pub/name
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXT:fail(f'{tid} public {side} audio missing/invalid: {name}')
            expected=str(detail.get(side+'_sha256') or '').lower()
            if expected and sha256(path)!=expected:fail(f'{tid} {side} audio SHA-256 mismatch')
            checked_audio+=1
        if str(row.get('pick_generated') or '').strip():fail(f'{tid} public template already contains a listener answer')

    report={'schema':1,'packet_valid':True,'trial_count':len(rows),'audio_files_checked':checked_audio,
            'answer_key_schema':key_raw.get('schema'),'public_fields':fields}
    if a.out:
        p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=='__main__':main()
