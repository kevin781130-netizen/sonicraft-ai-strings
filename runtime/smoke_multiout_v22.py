from __future__ import annotations
import argparse,socket,numpy as np
from protocol import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
    sr=48000;start=200000;end=start+sr//4
    ctrl=[.7,.5,.9,.85,.5,1.,1.,.2,.5,0.,.5,.5,.4,0.]
    ev=[EVENT.pack(start,EVENT_NOTE_ON,0,69,0,.8,68.,*ctrl),EVENT.pack(end-100,EVENT_NOTE_OFF,0,69,0,0.,68.,*ctrl)]
    h=RequestHeader(TYPE_RENDER,220,start,end,sr,len(ev),4,1,68.,.35,1<<25)
    with socket.create_connection(('127.0.0.1',a.port),timeout=5) as s:
        s.sendall(pack_request_header(h)+b''.join(ev));rh=unpack_response_header(recv_exact(s,RESP_HEADER.size));payload=recv_exact(s,rh.payload_bytes)
    x=np.frombuffer(payload,dtype='<f4').reshape(rh.frames,rh.channels)
    assert rh.status in (STATUS_OK,STATUS_CACHE_HIT) and rh.channels==34 and x.shape==(end-start,34)
    assert np.isfinite(x).all() and np.max(np.abs(x[:,:2]))>0
    assert np.max(np.abs(x[:,2:]))>0
    print('v2.2 MULTIOUT PASS',x.shape,'peak',float(np.max(np.abs(x))))
if __name__=='__main__':main()
