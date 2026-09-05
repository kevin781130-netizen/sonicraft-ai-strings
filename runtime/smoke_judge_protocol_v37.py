from __future__ import annotations
import argparse,socket
from protocol import *
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
    sr=48000;start=100000;end=start+sr//2
    ctrl=[.65,.5,.9,.86,.5,1,1,.18,.5,0,.5,.5,.38,0.]
    ev=[
      EVENT.pack(start,EVENT_NOTE_ON,0,69,0,.8,68.,*ctrl),
      EVENT.pack(end-100,EVENT_NOTE_OFF,0,69,0,0.,68.,*ctrl),
    ]
    flags=(1<<7)|(2<<8)|(10<<21)|(1<<26)|(1<<27)
    h=RequestHeader(TYPE_JUDGE,3701,start,end,sr,len(ev),4,1,68.,.35,flags)
    cfg=JUDGE_CONFIG.pack(.37,1<<1,0,0) # Favorite Take B should dominate identical mock renders.
    with socket.create_connection(('127.0.0.1',a.port),timeout=5) as s:
        s.sendall(pack_request_header(h)+cfg+b''.join(ev))
        rh=unpack_response_header(recv_exact(s,RESP_HEADER.size))
        payload=recv_exact(s,rh.payload_bytes)
    assert rh.status==STATUS_OK and rh.payload_bytes==JUDGE_RESULT.size
    version,winner,valid,*vals=JUDGE_RESULT.unpack(payload)
    assert version==1 and winner==1 and valid==0x0F,(version,winner,valid)
    assert len(vals)==24 and all(0<=x<=1 for x in vals)
    print('SONICRAFT v3.7 JUDGE PROTOCOL PASS winner=B scores=',[round(vals[i*6],4) for i in range(4)])
if __name__=='__main__':main()
