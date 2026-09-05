#!/usr/bin/env python3
"""Audit an experimental service-free ORT bundle. This does not promote sound parity by itself."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
BANNED=('python','torch','torchvision','torchaudio','site-packages')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bundle',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.bundle);arts=[];reasons=[]
    if not root.is_dir():reasons.append('bundle_missing')
    for p in sorted(x for x in root.rglob('*') if x.is_file()):
        rel=p.relative_to(root).as_posix();low=rel.lower()
        if any(x in low for x in BANNED):reasons.append('banned_runtime:'+rel)
        arts.append({'path':rel,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    names={Path(x['path']).name.lower() for x in arts}
    if 'onnxruntime.dll' not in names:reasons.append('onnxruntime.dll_missing')
    if not any(n.startswith('renderer_frontier.') and n.endswith(('.ort','.onnx')) for n in names):reasons.append('renderer_model_missing')
    if not any('strings_vae64_decoder' in n and n.endswith(('.ort','.onnx')) for n in names):reasons.append('decoder_model_missing')
    rep={'schema':1,'kind':'sonicraft_inprocess_ort_candidate_v25','bundle':str(root.resolve()),'artifacts':arts,'bytes':sum(x['bytes'] for x in arts),'python_free':not any(x.startswith('banned_runtime:') for x in reasons),'note':'Candidate only. Actual in-process C++ ORT rendering still requires numerical/audio parity before promotion.','reasons':reasons,'passed':not reasons};rep['evidence_id']=hashlib.sha256(json.dumps(rep,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8');print('INPROCESS ORT CANDIDATE V25','PASS' if rep['passed'] else 'FAIL',reasons)
    if reasons:raise SystemExit(3)
if __name__=='__main__':main()
