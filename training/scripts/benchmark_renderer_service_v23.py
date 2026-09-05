#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,hashlib,socket,time,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'runtime'))
from protocol import *
CTRL=[.66,.42,.91,.84,.5,1.,1.,.2,.5,0.,.5,.5,.38,0.]
def one(host,port,sr,seconds,note,reqid):
    end=int(sr*seconds);h=RequestHeader(TYPE_RENDER,reqid,0,end,sr,2,4,1,72.,.25,0);e=[]
    for ps,typ,vel in ((0,1,.78),(end-1,2,0.)):
        e.append(EVENT.pack(ps,typ,0,note,0,vel,72.,*CTRL))
    t=time.perf_counter()
    with socket.create_connection((host,port),timeout=120) as s:
        s.sendall(pack_request_header(h)+b''.join(e));rh=unpack_response_header(recv_exact(s,RESP_HEADER.size));payload=recv_exact(s,rh.payload_bytes)
    dt=time.perf_counter()-t
    if rh.status not in (STATUS_OK,STATUS_CACHE_HIT) or rh.channels not in (2,24) or len(payload)!=rh.payload_bytes:raise RuntimeError(f'bad render response {rh}')
    return dt,rh.status

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=49337);ap.add_argument('--seconds',type=float,default=2.0);ap.add_argument('--runs',type=int,default=8);ap.add_argument('--max-p95-rtf',type=float,default=1.0);ap.add_argument('--out',required=True);a=ap.parse_args()
    vals=[];statuses=[]
    for i in range(max(3,a.runs)):
        dt,st=one(a.host,a.port,48000,a.seconds,60+(i%12),230100+i);vals.append(dt/max(.001,a.seconds));statuses.append(st)
    s=sorted(vals);idx=min(len(s)-1,max(0,int(.95*len(s)+.999)-1));p95=s[idx];med=statistics.median(vals);passed=p95<=a.max_p95_rtf and not any(st==STATUS_MODEL_NOT_READY for st in statuses)
    rep={'schema':1,'kind':'sonicraft_runtime_benchmark_v23','runs':len(vals),'audio_seconds':a.seconds,'rtf':vals,'median_rtf':med,'p95_rtf':p95,'max_p95_rtf':a.max_p95_rtf,'passed':passed,'note':'RTF < 1 means faster than audio duration; benchmark must use production target hardware for promotion.'};rep['evidence_id']=hashlib.sha256(json.dumps(rep,sort_keys=True,separators=(',',':')).encode()).hexdigest();Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8');print('RUNTIME BENCH V23','PASS' if passed else 'FAIL','median',round(med,4),'p95',round(p95,4))
    if not passed:raise SystemExit(3)
if __name__=='__main__':main()
