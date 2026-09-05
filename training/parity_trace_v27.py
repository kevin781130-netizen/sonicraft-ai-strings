"""Stage-addressable differential traces for the v2.7 Native Parity Forge."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np

STAGES=('raw_controls','frontier_context','initial_latent','renderer_velocity','latent_after_step','final_latent','decoder_audio','stage_audio','final_mix')

def sha_obj(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def save_trace(path,scenario,arrays,meta=None):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    arr={k:np.asarray(v) for k,v in arrays.items() if k in STAGES}
    np.savez_compressed(path,**arr)
    manifest={'schema':2,'kind':'sonicraft_native_parity_trace_v27','scenario':scenario,'npz':path.name,'stages':list(arr),'meta':meta or {}}
    manifest['evidence_id']=sha_obj(manifest)
    path.with_suffix('.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

def metric(a,b):
    a=np.asarray(a,np.float64); b=np.asarray(b,np.float64)
    if a.shape!=b.shape:return {'shape_match':False,'max_abs':float('inf'),'rmse':float('inf'),'corr':-1.0}
    if not a.size:return {'shape_match':True,'max_abs':0.,'rmse':0.,'corr':1.}
    d=a-b; mx=float(np.max(np.abs(d))); rm=float(np.sqrt(np.mean(d*d)))
    aa=a.reshape(-1);bb=b.reshape(-1)
    corr=1. if mx==0 else (float(np.corrcoef(aa,bb)[0,1]) if aa.size>1 and np.std(aa)>1e-12 and np.std(bb)>1e-12 else 0.)
    return {'shape_match':True,'max_abs':mx,'rmse':rm,'corr':corr}

def first_divergence(ref,native,tolerances=None):
    tolerances=tolerances or {}
    for stage in STAGES:
        if stage not in ref or stage not in native:continue
        a=np.asarray(ref[stage]);b=np.asarray(native[stage]);tol=float(tolerances.get(stage,1e-6))
        if a.shape!=b.shape:return {'stage':stage,'kind':'shape','reference_shape':list(a.shape),'native_shape':list(b.shape)}
        d=np.abs(a.astype(np.float64)-b.astype(np.float64));bad=np.argwhere(d>tol)
        if bad.size:
            idx=tuple(int(x) for x in bad[0]);return {'stage':stage,'kind':'value','index':list(idx),'reference':float(a[idx]),'native':float(b[idx]),'abs_diff':float(d[idx]),'tolerance':tol}
    return None
