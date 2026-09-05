#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, subprocess, sys
from pathlib import Path
import numpy as np
import soundfile as sf
MIC_NAMES=('spot_l','spot_c','spot_r','tree_l','tree_c','tree_r','wide_l','wide_r','room_l','room_r','rear')

def resample(x,src,dst):
    if src==dst:return x.astype(np.float32,copy=False)
    n=max(1,int(round(len(x)*dst/src)));old=np.arange(len(x),dtype=np.float64);new=np.linspace(0,max(0,len(x)-1),n,dtype=np.float64)
    return np.stack([np.interp(new,old,x[:,c]) for c in range(x.shape[1])],1).astype(np.float32)

def deconv(rec,exc,reg_db=-70.0):
    n=1
    need=len(rec)+len(exc)-1
    while n<need:n<<=1
    X=np.fft.rfft(exc,n);floor=max(1e-18,float(np.max(np.abs(X)**2))*10**(reg_db/10.0));den=np.abs(X)**2+floor
    out=[]
    for c in range(rec.shape[1]):
        Y=np.fft.rfft(rec[:,c],n);h=np.fft.irfft(Y*np.conj(X)/den,n).astype(np.float32);out.append(h)
    return np.stack(out,1)

def crop_ir(h,taps):
    env=np.max(np.abs(h),axis=1);pk=int(np.argmax(env));pre=min(pk,32);start=pk-pre;seg=h[start:start+taps]
    if len(seg)<taps:seg=np.pad(seg,((0,taps-len(seg)),(0,0)))
    peak=max(1e-9,float(np.max(np.abs(seg))));seg=(seg/min(1.0,peak/.95)).astype(np.float32) if peak>.95 else seg.astype(np.float32)
    return seg,start,pk

def main():
    ap=argparse.ArgumentParser(description='Recover 11 clean-room scoring-stage IRs from SONICRAFT/user-owned sweep recordings.')
    ap.add_argument('--sweep',required=True);ap.add_argument('--recordings-dir',required=True);ap.add_argument('--ir-out-dir',required=True);ap.add_argument('--profile-out',required=True)
    ap.add_argument('--rights-confirmed',action='store_true');ap.add_argument('--session-note',required=True);ap.add_argument('--ir-seconds',type=float,default=1.5);ap.add_argument('--reg-db',type=float,default=-70.0);a=ap.parse_args()
    if not a.rights_confirmed:raise SystemExit('BLOCKED: --rights-confirmed is mandatory; only owned or explicitly licensed room measurements may be used.')
    sweep,sr=sf.read(a.sweep,dtype='float32',always_2d=True);exc=sweep[:,0];outdir=Path(a.ir_out_dir);outdir.mkdir(parents=True,exist_ok=True);recs=Path(a.recordings_dir);sources=[];taps=max(256,int(round(float(a.ir_seconds)*sr)))
    for name in MIC_NAMES:
        p=recs/(name+'.wav')
        if not p.is_file():raise SystemExit(f'missing sweep recording: {p}')
        y,ysr=sf.read(p,dtype='float32',always_2d=True);y=resample(y,int(ysr),int(sr));h=deconv(y,exc,float(a.reg_db));seg,start,pk=crop_ir(h,taps);op=outdir/(name+'.wav');sf.write(op,seg,int(sr),subtype='PCM_24')
        sources.append({'feed':name,'recording':p.name,'recording_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'recovered_ir_sha256':hashlib.sha256(op.read_bytes()).hexdigest(),'deconv_peak_sample':pk,'crop_start_sample':start})
    builder=Path(__file__).with_name('build_room_profile_v22.py');subprocess.run([sys.executable,str(builder),'--ir-dir',str(outdir),'--out',str(a.profile_out),'--sample-rate',str(sr),'--taps','128'],check=True)
    audit=Path(a.profile_out).with_suffix('.capture.json');body={'schema':1,'kind':'sonicraft_room_capture_v23','rights_confirmed':True,'session_note':a.session_note,'sweep_sha256':hashlib.sha256(Path(a.sweep).read_bytes()).hexdigest(),'sources':sources,'profile':str(Path(a.profile_out).name)};body['evidence_id']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest();audit.write_text(json.dumps(body,indent=2),encoding='utf-8');print('ROOM CAPTURE PASS',a.profile_out,body['evidence_id'])
if __name__=='__main__':main()
