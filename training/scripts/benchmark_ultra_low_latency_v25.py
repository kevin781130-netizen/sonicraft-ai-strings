#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,platform,socket,statistics,time
from pathlib import Path
import numpy as np
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'runtime'))
from protocol import *

def evidence(d):
    x=dict(d);x.pop('evidence_id',None);return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def backend_status(host,port):
    h=RequestHeader(TYPE_PING,259999,0,0,48000,0,4,0,72.0,.0,0)
    with socket.create_connection((host,port),timeout=5) as s:s.sendall(pack_request_header(h));r=unpack_response_header(recv_exact(s,RESP_HEADER.size))
    if r.flags&(1<<1):return 'ORT'
    if r.flags&(1<<2):return 'TORCH'
    if r.flags&(1<<3):return 'MOCK'
    return 'UNKNOWN'
def one(host,port,sr,ms,idx):
    frames=max(1,round(sr*ms/1000));start=idx*sr;end=start+frames;flags=1|(1<<7)|(((idx+31)&255)<<11)|(1<<19)|(1<<25)
    h=RequestHeader(TYPE_RENDER,250000+idx,start,end,sr,2,4,1,72.0,min(.08,ms/1000),flags);ctrl=[.62,.50,.90,.86,.50,1.,1.,.18,.50,0.,.50,.50,.38,0.]
    ev0=EVENT.pack(start,EVENT_NOTE_ON,0,69,0,.82,72.0,*ctrl);ev1=EVENT.pack(end-1,EVENT_NOTE_OFF,0,69,0,0.,72.0,*ctrl)
    with socket.create_connection((host,port),timeout=15) as s:
        s.settimeout(120);t0=time.perf_counter();s.sendall(pack_request_header(h)+ev0+ev1);rh=unpack_response_header(recv_exact(s,RESP_HEADER.size));_payload=recv_exact(s,rh.payload_bytes);dt=(time.perf_counter()-t0)*1000
    if rh.status not in (STATUS_OK,STATUS_CACHE_HIT) or rh.frames!=frames:raise RuntimeError(f'bad response {rh}')
    return dt,rh.status
def p95(xs):
    s=sorted(xs);return s[min(len(s)-1,max(0,int(np.ceil(.95*len(s)))-1))]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=49337);ap.add_argument('--sample-rate',type=int,default=48000);ap.add_argument('--trials',type=int,default=12)
    ap.add_argument('--attack-ms',type=float,default=40);ap.add_argument('--sustain-ms',type=float,default=80);ap.add_argument('--max-attack-service-p95-ms',type=float,default=35);ap.add_argument('--max-sustain-service-p95-ms',type=float,default=65);ap.add_argument('--wasapi-stream-latency-ms',type=float,default=0);ap.add_argument('--max-estimated-first-audio-ms',type=float,default=65);ap.add_argument('--out',required=True);a=ap.parse_args()
    backend=backend_status(a.host,a.port);att=[];sus=[];cached=0
    for i in range(max(5,a.trials)):
        x,st=one(a.host,a.port,a.sample_rate,a.attack_ms,i);att.append(x);cached+=st==STATUS_CACHE_HIT
        x,st=one(a.host,a.port,a.sample_rate,a.sustain_ms,1000+i);sus.append(x);cached+=st==STATUS_CACHE_HIT
    ap95,sp95=p95(att),p95(sus);estimated=ap95+max(0.,a.wasapi_stream_latency_ms);reasons=[]
    if platform.system()!='Windows':reasons.append('formal_ultra_low_latency_requires_windows')
    if backend not in ('ORT','TORCH'):reasons.append('production_backend_required')
    if cached:reasons.append('cache_hits_not_allowed_in_latency_evidence')
    if a.wasapi_stream_latency_ms<=0:reasons.append('measured_wasapi_stream_latency_required')
    if ap95>a.max_attack_service_p95_ms:reasons.append('attack_service_p95_too_slow')
    if sp95>a.max_sustain_service_p95_ms:reasons.append('sustain_service_p95_too_slow')
    if estimated>a.max_estimated_first_audio_ms:reasons.append('estimated_first_audio_too_slow')
    rep={'schema':1,'kind':'sonicraft_ultra_low_latency_benchmark_v25','platform':platform.system(),'sample_rate':a.sample_rate,'audio_engine':'WASAPI_EVENT_SHARED_IAUDIOCLIENT3','midi_timestamp_source':'WinMM_dwParam2_driver_timestamp','adaptive_quantum_ms':[40,80,160],'attack_quantum_ms':a.attack_ms,'sustain_quantum_ms':a.sustain_ms,'trials_per_quantum':max(5,a.trials),'attack_median_service_ms':statistics.median(att),'attack_p95_service_ms':ap95,'sustain_p95_service_ms':sp95,'wasapi_stream_latency_ms':a.wasapi_stream_latency_ms,'estimated_first_audio_ms':estimated,'backend':backend,'cache_hits':cached,'reasons':reasons,'passed':not reasons}
    rep['evidence_id']=evidence(rep);Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8');print('ULTRA LOW LATENCY V25','PASS' if rep['passed'] else 'FAIL',f'attack_p95={ap95:.1f}ms estimated={estimated:.1f}ms',reasons)
    if reasons:raise SystemExit(3)
if __name__=='__main__':main()
