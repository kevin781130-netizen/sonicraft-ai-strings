#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def evok(d):
    eid=d.get('evidence_id');x=dict(d);x.pop('evidence_id',None)
    return bool(eid) and hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()==eid
def bindok(d):
    root=Path(str(d.get('bundle','')));arts=d.get('artifacts') or []
    if not root.is_dir() or not arts:return False
    for e in arts:
        p=root/e['path']
        if not p.is_file() or p.stat().st_size!=int(e['bytes']) or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:return False
    return True
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--native-promotion',required=True);ap.add_argument('--realtime-benchmark',required=True);ap.add_argument('--shell-bundle',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();n=load(a.native_promotion);b=load(a.realtime_benchmark);s=load(a.shell_bundle);r=[]
    if not n.get('promotion_pass') or len(str(n.get('runtime_promotion_id','')))!=64:r.append('native_runtime_not_promoted')
    if not evok(b) or not b.get('passed') or float(b.get('deadline_miss_rate',1))>.01:r.append('realtime_benchmark_failed')
    if not evok(s) or not s.get('passed') or not bindok(s):r.append('shell_bundle_binding_failed')
    base={'schema':1,'kind':'sonicraft_realtime_product_promotion_v24','native_runtime_promotion_id':n.get('runtime_promotion_id'),'realtime_evidence_id':b.get('evidence_id'),'shell_bundle_evidence_id':s.get('evidence_id'),'p95_first_audio_ms':b.get('p95_first_audio_ms'),'deadline_miss_rate':b.get('deadline_miss_rate'),'reasons':r,'promotion_pass':not r};base['product_promotion_id']=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(base,indent=2),encoding='utf-8');print('REALTIME PRODUCT PROMOTION V24','PASS' if not r else 'FAIL',base['product_promotion_id'])
    if r:raise SystemExit(3)
if __name__=='__main__':main()
