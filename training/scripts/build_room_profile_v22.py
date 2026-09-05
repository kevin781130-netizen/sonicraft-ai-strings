#!/usr/bin/env python3
"""Build a SONICRAFT v2.2 directional room profile from user/SONICRAFT-owned IR WAVs.

Expected filenames are the 11 virtual feed names (spot_l.wav ... rear.wav). WAVs may be mono
or stereo. No proprietary measurements are included or downloaded by this tool.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import soundfile as sf

MIC_NAMES=('spot_l','spot_c','spot_r','tree_l','tree_c','tree_r','wide_l','wide_r','room_l','room_r','rear')
DEFAULT_PAN=(-.45,0,.45,-.55,0,.55,-.78,.78,-.62,.62,0.)

def resample_linear(x,src,dst):
    if src==dst:return x
    n=max(1,int(round(len(x)*dst/src)));old=np.linspace(0,1,len(x),endpoint=False);new=np.linspace(0,1,n,endpoint=False)
    if x.ndim==1:return np.interp(new,old,x).astype(np.float32)
    return np.stack([np.interp(new,old,x[:,c]) for c in range(x.shape[1])],1).astype(np.float32)

def onset(x):
    m=np.max(np.abs(x),axis=1) if x.ndim==2 else np.abs(x);pk=float(m.max(initial=0))
    if pk<=1e-12:return 0
    hit=np.flatnonzero(m>=pk*0.08);return int(hit[0]) if hit.size else 0

def fir_from_ir(x,start,taps):
    if x.ndim==1:x=x[:,None]
    seg=x[start:start+taps]
    if len(seg)<taps:seg=np.pad(seg,((0,taps-len(seg)),(0,0)))
    # Preserve L/R directional shape while globally normalizing for numerical safety.
    den=max(1e-9,float(np.sqrt(np.sum(seg*seg))))
    seg=(seg/den).astype(np.float32)
    if seg.shape[1]==1:return seg[:,0],seg[:,0]
    return seg[:,0],seg[:,1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ir-dir',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--sample-rate',type=int,default=48000);ap.add_argument('--taps',type=int,default=64);a=ap.parse_args()
    root=Path(a.ir_dir);taps=max(8,min(128,int(a.taps)));feeds={};sources=[];global_rms=[]
    raw={}
    for i,name in enumerate(MIC_NAMES):
        p=root/(name+'.wav')
        if not p.is_file():raise SystemExit(f'missing required IR: {p}')
        x,sr=sf.read(p,dtype='float32',always_2d=True);x=resample_linear(x,int(sr),int(a.sample_rate));raw[name]=(x,i,p)
        global_rms.append(float(np.sqrt(np.mean(x*x)+1e-12)))
        sources.append({'name':name,'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    ref=max(1e-9,max(global_rms))
    for name,(x,i,p) in raw.items():
        st=onset(x);l,r=fir_from_ir(x,st,taps);rms=float(np.sqrt(np.mean(x*x)+1e-12));
        feeds[name]={'delay_samples':st,'gain':float(np.clip(rms/ref,.05,1.5)),'pan':DEFAULT_PAN[i],
                     'left_fir':[float(v) for v in l],'right_fir':[float(v) for v in r]}
    out={'schema':1,'kind':'sonicraft_directional_room_profile','sample_rate':int(a.sample_rate),'taps':taps,
         'ownership_required':True,'clean_room_note':'Generated only from user/SONICRAFT-owned or explicitly licensed IRs. No competitor room measurements.',
         'sources':sources,'feeds':feeds}
    op=Path(a.out);op.parent.mkdir(parents=True,exist_ok=True);op.write_text(json.dumps(out,indent=2),encoding='utf-8')
    print('ROOM PROFILE PASS',op,'feeds',len(feeds),'taps',taps)
if __name__=='__main__':main()
