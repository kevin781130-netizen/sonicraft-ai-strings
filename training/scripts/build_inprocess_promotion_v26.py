#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def evok(d):
    eid=d.get('evidence_id');b=dict(d);b.pop('evidence_id',None)
    return bool(eid) and hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest()==eid
def bindok(d):
    root=Path(str(d.get('bundle','')));arts=d.get('artifacts') or []
    if not root.is_dir() or not arts:return False
    for e in arts:
        p=root/e['path']
        if not p.is_file() or p.stat().st_size!=int(e['bytes']) or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:return False
    return True
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bundle-evidence',required=True);ap.add_argument('--parity',required=True);ap.add_argument('--runtime-abx',required=True);ap.add_argument('--native-promotion',required=True);ap.add_argument('--ultra-low-latency-promotion',required=True);ap.add_argument('--out',required=True);ap.add_argument('--lock',required=True);a=ap.parse_args();b=load(a.bundle_evidence);p=load(a.parity);abx=load(a.runtime_abx);nat=load(a.native_promotion);lat=load(a.ultra_low_latency_promotion);r=[]
    if not evok(b) or not b.get('passed') or not bindok(b):r.append('bundle_binding_failed')
    if b.get('deployment_kind')!='pure-native-inprocess' or not b.get('python_free') or not b.get('service_free'):r.append('python_or_service_present')
    if str(b.get('platform','')).lower()!='windows':r.append('windows_production_bundle_required')
    if not evok(p) or not p.get('passed') or int(p.get('pair_count',0))<6:r.append('inprocess_parity_failed')
    if int(abx.get('schema',0))!=2 or not abx.get('transparency_pass') or int(abx.get('listener_count',0))<5 or int(abx.get('trial_count',0))<60:r.append('runtime_abx_failed_or_underpowered')
    if not nat.get('promotion_pass') or len(str(nat.get('runtime_promotion_id','')))!=64:r.append('v23_native_runtime_promotion_required')
    if not lat.get('promotion_pass') or len(str(lat.get('ultra_low_latency_promotion_id','')))!=64:r.append('v25_ultra_low_latency_promotion_required')
    base={'schema':1,'kind':'sonicraft_inprocess_neural_promotion_v26','bundle_evidence_id':b.get('evidence_id'),'parity_evidence_id':p.get('evidence_id'),'runtime_promotion_id':nat.get('runtime_promotion_id'),'ultra_low_latency_promotion_id':lat.get('ultra_low_latency_promotion_id'),'runtime_abx_accuracy':abx.get('accuracy'),'reasons':r,'promotion_pass':not r};base['inprocess_promotion_id']=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(base,indent=2),encoding='utf-8')
    if not r:
        root=Path(b['bundle']);roles=b['roles'];arts={e['path']:e for e in b['artifacts']}
        lines=['SONICRAFT_INPROCESS_PROMOTION_V26','promotion_id='+base['inprocess_promotion_id']]
        for role,key in [('renderer','renderer'),('decoder','decoder'),('ort_runtime','ort_runtime')]:
            rel=roles[key];lines.append(role+'='+rel);lines.append(role+'_sha256='+arts[rel]['sha256'])
        lines+=['parity_evidence_id='+p['evidence_id'],'runtime_promotion_id='+str(nat['runtime_promotion_id']),'ultra_low_latency_promotion_id='+str(lat['ultra_low_latency_promotion_id'])]
        Path(a.lock).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('INPROCESS NEURAL PROMOTION V26','PASS' if not r else 'FAIL',base['inprocess_promotion_id'],r)
    if r:raise SystemExit(3)
if __name__=='__main__':main()
