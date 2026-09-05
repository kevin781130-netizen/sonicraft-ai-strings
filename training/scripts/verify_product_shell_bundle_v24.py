#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def pe64(p:Path):
    try:
        with p.open('rb') as f:
            if f.read(2)!=b'MZ':return False
            f.seek(0x3c);off=int.from_bytes(f.read(4),'little');f.seek(off);return f.read(4)==b'PE\0\0' and f.read(2)==b'\x64\x86'
    except Exception:return False

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bundle',required=True);ap.add_argument('--out',required=True);ap.add_argument('--max-mib',type=float,default=170.0);a=ap.parse_args();root=Path(a.bundle)
    files=[p for p in root.rglob('*') if p.is_file()] if root.is_dir() else [];rel=lambda p:str(p.relative_to(root)).replace('\\','/')
    total=sum(p.stat().st_size for p in files);byname={p.name.lower():p for p in files};reasons=[]
    shell=byname.get('sonicraftaistringsproductshell.exe');svc=byname.get('sonicraft_ai_renderer_service.exe') or byname.get('sonicraft_renderer_service.exe')
    if not shell:reasons.append('product_shell_exe_missing')
    elif not pe64(shell):reasons.append('product_shell_not_pe64')
    if not svc:reasons.append('renderer_service_exe_missing')
    elif not pe64(svc):reasons.append('renderer_service_not_pe64')
    if total>a.max_mib*1024**2:reasons.append('bundle_over_limit')
    if any(any(x in rel(p).lower() for x in ('torch/','torch\\','torch_cpu','torch_cuda','pytorch')) for p in files):reasons.append('torch_present')
    arts=[{'path':rel(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files,key=lambda x:rel(x).lower())]
    rep={'schema':1,'kind':'sonicraft_product_shell_bundle_v24','bundle':str(root),'files':len(files),'bytes':total,'mib':total/1024**2,'max_mib':a.max_mib,'reasons':reasons,'passed':not reasons,'artifacts':arts};rep['evidence_id']=hashlib.sha256(json.dumps(rep,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8');print('PRODUCT SHELL BUNDLE V24','PASS' if not reasons else 'FAIL',reasons)
    if reasons:raise SystemExit(3)
if __name__=='__main__':main()
