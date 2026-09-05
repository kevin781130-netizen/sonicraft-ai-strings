from __future__ import annotations
import argparse,socket
from protocol import *

def enc(part,lane):return (part&3)|((lane+1)<<2)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
    sr=48000;end=12000
    c=[.62,.5,.9,.86,.5,1,1,.18,.5,0,.5,.5,.38,0.]
    ev=[
      EVENT.pack(0,EVENT_CONTROL,enc(0,0),120,0,.75,80.,*c),
      EVENT.pack(0,EVENT_CONTROL,enc(0,0),121,0,.50,80.,*c),
      EVENT.pack(1000,EVENT_NOTE_ON,enc(0,0),72,0,.8,80.,*c),
      EVENT.pack(end-1,EVENT_NOTE_OFF,enc(0,0),72,0,0.,80.,*c),
    ]
    flags=(1<<7)|(1<<25)
    h=RequestHeader(TYPE_RENDER,4401,0,end,sr,len(ev),4,1,80.,.35,flags)
    with socket.create_connection(('127.0.0.1',a.port),timeout=5) as s:
        s.sendall(pack_request_header(h)+b''.join(ev))
        rh=unpack_response_header(recv_exact(s,RESP_HEADER.size))
        payload=recv_exact(s,rh.payload_bytes)
    assert rh.status in (STATUS_OK,STATUS_CACHE_HIT)
    assert rh.frames==end and rh.channels==34 and len(payload)==end*34*4
    print('SONICRAFT v4.4 ensemble timing service protocol PASS',rh.frames,rh.channels)

if __name__=='__main__':main()
