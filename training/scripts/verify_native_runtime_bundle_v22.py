#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

BANNED=('torch','torchvision','torchaudio','pytorch','descript_audio_codec')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bundle',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--max-mib',type=float,default=160.0);ap.add_argument('--require-models',action='store_true');a=ap.parse_args()
    root=Path(a.bundle)
    if not root.is_dir():raise SystemExit(f'bundle missing: {root}')
    files=[p for p in root.rglob('*') if p.is_file()];total=sum(p.stat().st_size for p in files)
    offenders=[]
    for p in files:
        low=str(p.relative_to(root)).lower()
        if any(x in low for x in BANNED):offenders.append(low)
    ort=[p for p in files if p.name.lower() in ('onnxruntime.dll','libonnxruntime.so','libonnxruntime.dylib')]
    models=[p for p in files if p.suffix.lower() in ('.ort','.onnx')]
    passed=bool(ort) and not offenders and total<=a.max_mib*1024*1024 and (not a.require_models or len(models)>=2)
    artifacts=[]
    for p in sorted(files,key=lambda q:str(q.relative_to(root)).lower()):
        rel=str(p.relative_to(root)).replace('\\','/')
        artifacts.append({'path':rel,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    report={'schema':2,'kind':'sonicraft_native_runtime_footprint_v22','bundle':str(root),'files':len(files),'bytes':total,
            'mib':total/(1024**2),'max_mib':float(a.max_mib),'onnxruntime_binaries':[str(p.relative_to(root)).replace('\\','/') for p in ort],
            'models':[str(p.relative_to(root)).replace('\\','/') for p in models],'artifacts':artifacts,
            'banned_framework_hits':offenders,'passed':passed}
    raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode();report['evidence_id']=hashlib.sha256(raw).hexdigest()
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('NATIVE RUNTIME FOOTPRINT',f"{report['mib']:.2f} MiB",'PASS' if passed else 'FAIL')
    if not passed:raise SystemExit(3)
if __name__=='__main__':main()
