#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
BANNED=('torch','torchvision','torchaudio','pytorch','descript_audio_codec')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bundle',required=True);ap.add_argument('--out',required=True);ap.add_argument('--max-mib',type=float,default=160.0)
    ap.add_argument('--deployment-kind',choices=['embedded-python-ort','pure-native-ort'],default='embedded-python-ort');a=ap.parse_args();root=Path(a.bundle)
    if not root.is_dir():raise SystemExit(f'bundle missing: {root}')
    files=[p for p in root.rglob('*') if p.is_file()];total=sum(p.stat().st_size for p in files);rel=lambda p:str(p.relative_to(root)).replace('\\','/')
    offenders=[rel(p) for p in files if any(x in rel(p).lower() for x in BANNED)]
    low=[rel(p).lower() for p in files];models=[rel(p) for p in files if p.suffix.lower() in ('.ort','.onnx')]
    ort=[rel(p) for p in files if 'onnxruntime' in p.name.lower() and p.suffix.lower() in ('.dll','.so','.dylib','.pyd')]
    reasons=[]
    if offenders:reasons.append('banned_framework_present')
    if total>float(a.max_mib)*1024**2:reasons.append('footprint_over_limit')
    if len(models)<2:reasons.append('renderer_or_decoder_model_missing')
    if not ort:reasons.append('onnxruntime_binary_missing')
    if a.deployment_kind=='embedded-python-ort':
        if not any(Path(x).name.startswith('python') and Path(x).suffix.lower()=='.dll' for x in low):reasons.append('embedded_python_dll_missing')
        if not any(Path(x).name=='python.exe' for x in low):reasons.append('embedded_python_exe_missing')
        if not any('/numpy' in ('/'+x) or Path(x).name.startswith('numpy') for x in low):reasons.append('numpy_missing')
        if not any(Path(x).name=='renderer_service.py' for x in low):reasons.append('renderer_service_missing')
    else:
        if not any(Path(x).name.lower() in ('sonicraft_renderer_service.exe','sonicraft_ai_renderer_service.exe') for x in low):reasons.append('native_service_exe_missing')
        if any('python' in Path(x).name.lower() for x in low):reasons.append('python_present_in_pure_native_bundle')
    arts=[{'path':rel(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files,key=lambda q:rel(q).lower())]
    rep={'schema':3,'kind':'sonicraft_native_runtime_footprint_v23','deployment_kind':a.deployment_kind,'bundle':str(root),'files':len(files),'bytes':total,'mib':total/(1024**2),'max_mib':float(a.max_mib),'models':models,'onnxruntime_binaries':ort,'banned_framework_hits':offenders,'reasons':reasons,'passed':not reasons,'artifacts':arts}
    rep['evidence_id']=hashlib.sha256(json.dumps(rep,sort_keys=True,separators=(',',':')).encode()).hexdigest();op=Path(a.out);op.parent.mkdir(parents=True,exist_ok=True);op.write_text(json.dumps(rep,indent=2),encoding='utf-8')
    print('NATIVE RUNTIME V23',a.deployment_kind,f"{rep['mib']:.2f} MiB",'PASS' if not reasons else 'FAIL',reasons)
    if reasons:raise SystemExit(3)
if __name__=='__main__':main()
