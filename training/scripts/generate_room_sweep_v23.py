#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, math
from pathlib import Path
import numpy as np
import soundfile as sf

def main():
    ap=argparse.ArgumentParser(description='Generate a SONICRAFT-owned logarithmic room-measurement sweep.')
    ap.add_argument('--out',required=True);ap.add_argument('--meta');ap.add_argument('--sample-rate',type=int,default=48000)
    ap.add_argument('--seconds',type=float,default=8.0);ap.add_argument('--f0',type=float,default=20.0);ap.add_argument('--f1',type=float,default=20000.0)
    ap.add_argument('--level-dbfs',type=float,default=-12.0);ap.add_argument('--lead-seconds',type=float,default=1.0);ap.add_argument('--tail-seconds',type=float,default=2.0)
    a=ap.parse_args();sr=max(8000,int(a.sample_rate));T=max(1.0,float(a.seconds));f0=max(5.,float(a.f0));f1=min(.48*sr,max(f0*2,float(a.f1)))
    n=int(round(T*sr));t=np.arange(n,dtype=np.float64)/sr;L=T/math.log(f1/f0);phase=2*math.pi*f0*L*(np.exp(t/L)-1.0)
    amp=10**(float(a.level_dbfs)/20.0);w=np.sin(np.pi*np.clip(t/T,0,1))**2;sweep=(np.sin(phase)*w*amp).astype(np.float32)
    lead=np.zeros(int(round(max(0,a.lead_seconds)*sr)),np.float32);tail=np.zeros(int(round(max(0,a.tail_seconds)*sr)),np.float32);x=np.concatenate([lead,sweep,tail])
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);sf.write(out,x,sr,subtype='PCM_24')
    meta={'schema':1,'kind':'sonicraft_room_sweep_v23','sample_rate':sr,'sweep_seconds':T,'f0_hz':f0,'f1_hz':f1,'level_dbfs':float(a.level_dbfs),'lead_samples':len(lead),'sweep_samples':n,'tail_samples':len(tail),'wav_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'clean_room':True}
    mp=Path(a.meta) if a.meta else out.with_suffix('.json');mp.write_text(json.dumps(meta,indent=2),encoding='utf-8');print('ROOM SWEEP PASS',out,meta['wav_sha256'])
if __name__=='__main__':main()
