#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def evidence_ok(d):
    eid=d.get('evidence_id')
    if not eid:return True
    body=dict(d);body.pop('evidence_id',None)
    got=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return got==eid
def artifact_binding_ok(f):
    root=Path(str(f.get('bundle','')))
    arts=f.get('artifacts') or []
    if int(f.get('schema',0))>=2 and (not root.is_dir() or not arts):return False
    for ent in arts:
        p=root/str(ent.get('path',''))
        if not p.is_file() or p.stat().st_size!=int(ent.get('bytes',-1)):return False
        if hashlib.sha256(p.read_bytes()).hexdigest()!=ent.get('sha256'):return False
    return True
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--footprint',required=True);ap.add_argument('--numerical',required=True);ap.add_argument('--runtime-abx',required=True);ap.add_argument('--acoustic-promotion',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    f=load(a.footprint);n=load(a.numerical);abx=load(a.runtime_abx);ac=load(a.acoustic_promotion);reasons=[]
    if not evidence_ok(f):reasons.append('footprint_evidence_tampered')
    if not artifact_binding_ok(f):reasons.append('footprint_artifacts_changed')
    if not evidence_ok(n):reasons.append('numerical_evidence_tampered')
    if not f.get('passed'):reasons.append('footprint_failed')
    if float(f.get('mib',1e9))>160:reasons.append('footprint_over_160mib')
    if f.get('banned_framework_hits'):reasons.append('torch_or_banned_framework_present')
    if not n.get('passed') or int(n.get('pair_count',0))<1:reasons.append('numerical_parity_failed')
    if int(abx.get('schema',0))!=2 or not abx.get('transparency_pass'):reasons.append('runtime_abx_failed')
    if int(abx.get('listener_count',0))<5 or int(abx.get('trial_count',0))<60:reasons.append('runtime_abx_underpowered')
    if not ac.get('promotion_pass') or not ac.get('promotion_id'):reasons.append('acoustic_promotion_missing')
    base={'schema':1,'kind':'sonicraft_native_runtime_promotion_v22','runtime':'onnxruntime-reduced','acoustic_promotion_id':ac.get('promotion_id'),
          'footprint_evidence_id':f.get('evidence_id'),'numerical_evidence_id':n.get('evidence_id'),'runtime_abx_accuracy':abx.get('accuracy'),'reasons':reasons,'promotion_pass':not reasons}
    base['runtime_promotion_id']=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(base,indent=2),encoding='utf-8')
    print('NATIVE RUNTIME PROMOTION','PASS' if not reasons else 'FAIL',base['runtime_promotion_id'])
    if reasons:raise SystemExit(3)
if __name__=='__main__':main()
