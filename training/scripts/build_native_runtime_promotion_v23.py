#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def evidence_ok(d):
    eid=d.get('evidence_id')
    if not eid:return False
    b=dict(d);b.pop('evidence_id',None);return hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest()==eid
def artifact_binding_ok(f):
    root=Path(str(f.get('bundle','')));arts=f.get('artifacts') or []
    if not root.is_dir() or not arts:return False
    for e in arts:
        p=root/str(e.get('path',''))
        if not p.is_file() or p.stat().st_size!=int(e.get('bytes',-1)) or hashlib.sha256(p.read_bytes()).hexdigest()!=e.get('sha256'):return False
    return True
def main():
    ap=argparse.ArgumentParser();
    for n in ('footprint','numerical','runtime_abx','benchmark','acoustic_promotion'):ap.add_argument('--'+n.replace('_','-'),dest=n,required=True)
    ap.add_argument('--out',required=True);a=ap.parse_args();f=load(a.footprint);n=load(a.numerical);abx=load(a.runtime_abx);bench=load(a.benchmark);ac=load(a.acoustic_promotion);reasons=[]
    if int(f.get('schema',0))!=3 or not evidence_ok(f) or not artifact_binding_ok(f):reasons.append('footprint_or_artifact_binding_failed')
    if not f.get('passed') or float(f.get('mib',1e9))>160 or f.get('banned_framework_hits'):reasons.append('footprint_policy_failed')
    if not evidence_ok(n) or not n.get('passed') or int(n.get('pair_count',0))<1:reasons.append('numerical_parity_failed')
    if int(abx.get('schema',0))!=2 or not abx.get('transparency_pass') or int(abx.get('listener_count',0))<5 or int(abx.get('trial_count',0))<60:reasons.append('runtime_abx_failed_or_underpowered')
    if not evidence_ok(bench) or not bench.get('passed') or float(bench.get('p95_rtf',1e9))>float(bench.get('max_p95_rtf',1.0)):reasons.append('runtime_performance_failed')
    if not ac.get('promotion_pass') or not ac.get('promotion_id'):reasons.append('acoustic_promotion_missing')
    base={'schema':2,'kind':'sonicraft_native_runtime_promotion_v23','deployment_kind':f.get('deployment_kind'),'runtime':'onnxruntime-reduced','acoustic_promotion_id':ac.get('promotion_id'),'footprint_evidence_id':f.get('evidence_id'),'numerical_evidence_id':n.get('evidence_id'),'benchmark_evidence_id':bench.get('evidence_id'),'runtime_abx_accuracy':abx.get('accuracy'),'p95_rtf':bench.get('p95_rtf'),'reasons':reasons,'promotion_pass':not reasons};base['runtime_promotion_id']=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(base,indent=2),encoding='utf-8');print('NATIVE RUNTIME PROMOTION V23','PASS' if not reasons else 'FAIL',base['runtime_promotion_id'])
    if reasons:raise SystemExit(3)
if __name__=='__main__':main()
