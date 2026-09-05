#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
BANNED=('python','site-packages','torch','torchvision','torchaudio','renderer_service.py','sonicraft_renderer_service.exe','shadow_renderer_service')

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def pe64(p):
    try:
        b=p.read_bytes()[:4096]
        if len(b)<0x40 or b[:2]!=b'MZ':return False
        off=int.from_bytes(b[0x3c:0x40],'little')
        if off+26>len(b) or b[off:off+4]!=b'PE\0\0':return False
        machine=int.from_bytes(b[off+4:off+6],'little');opt=int.from_bytes(b[off+24:off+26],'little')
        return machine==0x8664 and opt==0x20b
    except Exception:return False

def evid(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bundle',required=True);ap.add_argument('--out',required=True);ap.add_argument('--max-mib',type=float,default=160.0);ap.add_argument('--platform',default='Windows');a=ap.parse_args();root=Path(a.bundle);reasons=[]
    if not root.is_dir():raise SystemExit(f'bundle missing: {root}')
    files=sorted((p for p in root.rglob('*') if p.is_file()),key=lambda p:p.as_posix().lower());arts=[];roles={}
    for p in files:
        rel=p.relative_to(root).as_posix();low=rel.lower();arts.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
        if any(x in low for x in BANNED):reasons.append('banned_service_or_framework:'+rel)
        n=p.name.lower()
        if n in ('onnxruntime.dll','libonnxruntime.so','libonnxruntime.dylib'):roles.setdefault('ort_runtime',rel)
        if n.startswith('renderer_frontier.') and p.suffix.lower() in ('.ort','.onnx'):roles.setdefault('renderer',rel)
        if 'strings_vae64_decoder' in n and p.suffix.lower() in ('.ort','.onnx'):roles.setdefault('decoder',rel)
        if n=='sonicraftaistringsproductshell.exe':roles.setdefault('product_shell',rel)
    total=sum(x['bytes'] for x in arts);mib=total/1024**2
    for k in ('ort_runtime','renderer','decoder'):
        if k not in roles:reasons.append(k+'_missing')
    if str(a.platform).lower()=='windows':
        if 'product_shell' not in roles:reasons.append('product_shell_missing')
        elif not pe64(root/roles['product_shell']):reasons.append('product_shell_not_pe64')
        if 'ort_runtime' in roles and not pe64(root/roles['ort_runtime']):reasons.append('ort_runtime_not_pe64')
    if mib>float(a.max_mib):reasons.append('footprint_over_limit')
    rep={'schema':1,'kind':'sonicraft_inprocess_bundle_v26','deployment_kind':'pure-native-inprocess','platform':a.platform,'bundle':str(root.resolve()),'bytes':total,'mib':mib,'max_mib':float(a.max_mib),'roles':roles,'artifacts':arts,'python_free':not any('python' in x.lower() for x in [e['path'] for e in arts]),'service_free':not any('service' in x.lower() for x in [e['path'] for e in arts]),'reasons':reasons,'passed':not reasons};rep['evidence_id']=evid(rep);Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8');print('INPROCESS BUNDLE V26','PASS' if rep['passed'] else 'FAIL',f"{mib:.2f} MiB",reasons)
    if reasons:raise SystemExit(3)
if __name__=='__main__':main()
