#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import soundfile as sf

def read(p):
    x,sr=sf.read(p,dtype='float32',always_2d=True);return x,int(sr)
def corr(a,b):
    a=a.reshape(-1).astype(np.float64);b=b.reshape(-1).astype(np.float64);a-=a.mean();b-=b.mean();d=np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.dot(a,b)/d) if d>1e-15 else float(np.allclose(a,b))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--torch-dir',required=True);ap.add_argument('--ort-dir',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--min-corr',type=float,default=.999);ap.add_argument('--max-nrmse',type=float,default=.01);a=ap.parse_args()
    td=Path(a.torch_dir);od=Path(a.ort_dir);rows=[]
    for tp in sorted(td.glob('*.wav')):
        op=od/tp.name
        if not op.is_file():continue
        x,sx=read(tp);y,sy=read(op)
        if sx!=sy or x.shape!=y.shape:rows.append({'file':tp.name,'pass':False,'reason':'shape_or_rate_mismatch'});continue
        err=x-y;rmse=float(np.sqrt(np.mean(err*err)));den=max(1e-8,float(np.sqrt(np.mean(x*x))));nrmse=rmse/den;c=corr(x,y)
        rows.append({'file':tp.name,'corr':c,'rmse':rmse,'nrmse':nrmse,'max_abs':float(np.max(np.abs(err))),'pass':c>=a.min_corr and nrmse<=a.max_nrmse})
    passed=bool(rows) and all(r.get('pass') for r in rows)
    rep={'schema':1,'kind':'sonicraft_runtime_numerical_parity_v22','pair_count':len(rows),'min_corr':a.min_corr,'max_nrmse':a.max_nrmse,'pairs':rows,'passed':passed}
    rep['evidence_id']=hashlib.sha256(json.dumps(rep,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8')
    print('RUNTIME NUMERICAL PARITY',len(rows),'pairs','PASS' if passed else 'FAIL')
    if not passed:raise SystemExit(3)
if __name__=='__main__':main()
