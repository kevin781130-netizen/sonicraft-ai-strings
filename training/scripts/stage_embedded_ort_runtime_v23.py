#!/usr/bin/env python3
"""Stage a minimal no-PyTorch embedded-Python + ONNX Runtime consumer bundle.

Inputs are already-acquired/licensed runtime artifacts. This tool downloads nothing.
It copies only the Python embeddable runtime, NumPy, ONNX Runtime, SONICRAFT runtime code,
and promoted ORT model artifacts, then emits a hashed deployment manifest.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BANNED=('torch','torchvision','torchaudio','pytorch','descript_audio_codec')
PKG_PREFIX=('numpy','onnxruntime')

def cp(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if src.is_dir():shutil.copytree(src,dst,dirs_exist_ok=True)
    else:shutil.copy2(src,dst)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--python-home',required=True);ap.add_argument('--model-dir',required=True);ap.add_argument('--out',required=True);ap.add_argument('--max-mib',type=float,default=160.0);a=ap.parse_args()
    py=Path(a.python_home);models=Path(a.model_dir);out=Path(a.out)
    if not py.is_dir():raise SystemExit(f'python home missing: {py}')
    if not models.is_dir():raise SystemExit(f'model dir missing: {models}')
    if out.exists():shutil.rmtree(out)
    out.mkdir(parents=True)
    # CPython embeddable root. Keep DLL/PYD/stdlib zip/launcher only; omit pip, tests and docs.
    patterns=('python*.dll','python*.exe','python*.zip','python*._pth','vcruntime*.dll','*.pyd')
    copied=[]
    for pat in patterns:
        for p in py.glob(pat):cp(p,out/p.name);copied.append(p.name)
    if not any(n.lower().startswith('python') and n.lower().endswith('.dll') for n in copied):raise SystemExit('embedded Python DLL not found')
    sp=None
    for cand in (py/'Lib'/'site-packages',py/'site-packages'):
        if cand.is_dir():sp=cand;break
    if sp is None:raise SystemExit('site-packages missing; prepare embeddable Python with NumPy + ONNX Runtime first')
    dstsp=out/'Lib'/'site-packages';dstsp.mkdir(parents=True)
    found={k:False for k in PKG_PREFIX}
    for p in sp.iterdir():
        low=p.name.lower()
        if any(low.startswith(k) for k in PKG_PREFIX):
            if any(b in low for b in BANNED):continue
            cp(p,dstsp/p.name)
            for k in PKG_PREFIX:
                if low.startswith(k):found[k]=True
    if not all(found.values()):raise SystemExit(f'missing required packages: {[k for k,v in found.items() if not v]}')
    # ORT-only Python service code. Runtime model definitions/checkpoints are not copied here.
    rdst=out/'Runtime';rdst.mkdir()
    for p in (ROOT/'runtime').glob('*.py'):
        cp(p,rdst/p.name)
    mdst=out/'Models';cp(models,mdst)
    # Fail if any forbidden framework leaked into bundle.
    bad=[]
    for p in out.rglob('*'):
        if p.is_file() and any(b in str(p.relative_to(out)).lower() for b in BANNED):bad.append(str(p.relative_to(out)))
    if bad:raise SystemExit(f'forbidden framework leaked into embedded runtime: {bad[:10]}')
    launcher=out/'START_RENDERER_ORT.cmd';launcher.write_text('@echo off\r\nset SONICRAFT_RUNTIME=ort\r\nset PYTHONPATH=%~dp0Runtime;%~dp0Lib\\site-packages\r\n"%~dp0python.exe" "%~dp0Runtime\\renderer_service.py" --backend ort %*\r\n',encoding='utf-8')
    files=[p for p in out.rglob('*') if p.is_file()];total=sum(p.stat().st_size for p in files);arts=[]
    for p in sorted(files,key=lambda q:str(q.relative_to(out)).lower()):arts.append({'path':str(p.relative_to(out)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    rep={'schema':1,'kind':'sonicraft_embedded_ort_bundle_v23','deployment_kind':'embedded-python-ort','files':len(files),'bytes':total,'mib':total/(1024**2),'max_mib':float(a.max_mib),'passed':total<=float(a.max_mib)*1024**2 and not bad,'artifacts':arts}
    rep['evidence_id']=hashlib.sha256(json.dumps(rep,sort_keys=True,separators=(',',':')).encode()).hexdigest();(out/'deployment_manifest_v23.json').write_text(json.dumps(rep,indent=2),encoding='utf-8')
    print('EMBEDDED ORT STAGE',f"{rep['mib']:.2f} MiB",'PASS' if rep['passed'] else 'FAIL')
    if not rep['passed']:raise SystemExit(3)
if __name__=='__main__':main()
