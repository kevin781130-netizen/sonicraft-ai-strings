#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
REQ={'manual','assist','polyphony','q4_phrase','retake','multiout'}
def evok(d):
 eid=d.get('evidence_id');b=dict(d);b.pop('evidence_id',None);return bool(eid) and hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest()==eid
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--diff-dir',required=True);ap.add_argument('--v26-promotion',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();rows=[];seen=set();reasons=[]
 for p in sorted(Path(a.diff_dir).glob('*.json')):
  d=json.loads(p.read_text());sc=d.get('scenario');
  if d.get('kind')!='sonicraft_native_trace_diff_v27':continue
  seen.add(sc);rows.append({'scenario':sc,'evidence_id':d.get('evidence_id')});
  if not evok(d) or not d.get('passed'):reasons.append(f'{sc}:trace_parity_failed')
 miss=REQ-seen
 if miss:reasons.append('missing:'+','.join(sorted(miss)))
 old=json.loads(Path(a.v26_promotion).read_text());
 if not old.get('promotion_pass') or len(str(old.get('inprocess_promotion_id','')))!=64:reasons.append('v26_inprocess_promotion_required')
 base={'schema':1,'kind':'sonicraft_native_parity_promotion_v27','trace_suite':rows,'v26_inprocess_promotion_id':old.get('inprocess_promotion_id'),'reasons':reasons,'promotion_pass':not reasons};base['native_parity_promotion_id']=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(base,indent=2),encoding='utf-8');print('NATIVE PARITY PROMOTION V27','PASS' if not reasons else 'FAIL',reasons);raise SystemExit(0 if not reasons else 3)
if __name__=='__main__':main()
