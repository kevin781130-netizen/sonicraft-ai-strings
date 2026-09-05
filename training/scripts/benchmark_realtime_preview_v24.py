#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,socket,statistics,time
from pathlib import Path
import numpy as np
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'runtime'))
from protocol import *

def backend_status(host,port):
    h=RequestHeader(TYPE_PING,239999,0,0,48000,0,4,0,72.0,.0,0)
    with socket.create_connection((host,port),timeout=5) as s:
        s.sendall(pack_request_header(h));r=unpack_response_header(recv_exact(s,RESP_HEADER.size))
    if r.flags&(1<<1):return 'ORT'
    if r.flags&(1<<2):return 'TORCH'
    if r.flags&(1<<3):return 'MOCK'
    return 'UNKNOWN'

def one(host,port,sr,quantum,idx):
    start=idx*quantum;end=start+quantum;nonce=(idx+1)&255
    # assist + polyphony + multiout + unique retake nonce to avoid cache benchmarking.
    flags=1 | (1<<7) | (nonce<<11) | (1<<19) | (1<<25)
    h=RequestHeader(TYPE_RENDER,240000+idx,start,end,sr,2,4,1,72.0,.08,flags)
    ctrl=[.62,.50,.90,.86,.50,1.,1.,.18,.50,0.,.50,.50,.38,0.]
    ev0=EVENT.pack(max(0,start-sr),EVENT_NOTE_ON,0,69,0,.82,72.0,*ctrl)
    ev1=EVENT.pack(end-1,EVENT_NOTE_OFF,0,69,0,0.0,72.0,*ctrl)
    with socket.create_connection((host,port),timeout=15) as s:
        s.settimeout(120);t0=time.perf_counter();s.sendall(pack_request_header(h)+ev0+ev1);rh=unpack_response_header(recv_exact(s,RESP_HEADER.size));payload=recv_exact(s,rh.payload_bytes);ms=(time.perf_counter()-t0)*1000.0
    if rh.status not in (STATUS_OK,STATUS_CACHE_HIT) or rh.frames!=quantum or rh.channels not in (2,24):raise RuntimeError(f'bad response {rh}')
    if len(payload)!=rh.frames*rh.channels*4:raise RuntimeError('payload mismatch')
    return ms,rh.status

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=49337);ap.add_argument('--sample-rate',type=int,default=48000);ap.add_argument('--quantum-ms',type=float,default=160.0);ap.add_argument('--trials',type=int,default=20);ap.add_argument('--max-p95-ms',type=float,default=120.0);ap.add_argument('--out',required=True);a=ap.parse_args()
    quantum=max(1,round(a.sample_rate*a.quantum_ms/1000.0));backend=backend_status(a.host,a.port);times=[];cached=0
    for i in range(max(5,a.trials)):
        ms,st=one(a.host,a.port,a.sample_rate,quantum,i);times.append(ms);cached+=st==STATUS_CACHE_HIT
    s=sorted(times);p95=s[min(len(s)-1,max(0,int(np.ceil(.95*len(s)))-1))];med=statistics.median(times);deadline=float(a.quantum_ms);miss=sum(x>deadline for x in times);miss_rate=miss/len(times)
    rep={'schema':1,'kind':'sonicraft_realtime_preview_benchmark_v24','sample_rate':a.sample_rate,'quantum_ms':float(a.quantum_ms),'trials':len(times),'median_first_audio_ms':med,'p95_first_audio_ms':p95,'max_p95_ms':float(a.max_p95_ms),'deadline_miss_rate':miss_rate,'cache_hits':int(cached),'backend':backend,'passed':backend in ('ORT','TORCH') and p95<=a.max_p95_ms and miss_rate<=.01 and cached==0}
    rep['evidence_id']=hashlib.sha256(json.dumps(rep,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8');print('REALTIME PREVIEW V24','PASS' if rep['passed'] else 'FAIL',f"p95={p95:.1f}ms miss={miss_rate:.3f}")
    if not rep['passed']:raise SystemExit(3)
if __name__=='__main__':main()
