from __future__ import annotations
import argparse,socket,struct,time,numpy as np
from protocol import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
    sr=48000; start=100000; end=start+sr
    ctrl=[.7,.5,.9,.85,.5,1.,1.,.15,.5,0.,.5,.5,.4,0.]
    ev=[EVENT.pack(start,EVENT_NOTE_ON,0,69,0,.8,68.,*ctrl), EVENT.pack(start+sr//2,EVENT_NOTE_OFF,0,69,0,0.,68.,*ctrl)]
    h=RequestHeader(TYPE_RENDER,123,start,end,sr,len(ev),4,1,68.,.35,0)
    with socket.create_connection(('127.0.0.1',a.port),timeout=5) as s:
        s.sendall(pack_request_header(h)+b''.join(ev)); rh=unpack_response_header(recv_exact(s,RESP_HEADER.size)); payload=recv_exact(s,rh.payload_bytes) if rh.payload_bytes else b''
    print('status',rh.status,'frames',rh.frames,'bytes',len(payload)); assert rh.status in (STATUS_OK,STATUS_CACHE_HIT) and rh.frames==sr
    x=np.frombuffer(payload,dtype='<f4'); assert np.isfinite(x).all() and np.max(np.abs(x))>0
    print('PASS peak',float(np.max(np.abs(x))))
if __name__=='__main__': main()
