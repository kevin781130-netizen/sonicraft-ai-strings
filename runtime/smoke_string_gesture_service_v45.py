from __future__ import annotations
import argparse,socket
from protocol import *
def enc(part,lane):return (part&3)|((lane+1)<<2)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
    sr=48000;end=12000
    lo=[.42,.25,.9,.86,.5,1,1,.18,.48,1/11,.52,.5,.35,0.]
    hi=[.78,.68,.9,.86,.5,1,1,.18,.57,1/11,.34,.5,.66,0.]
    ev=[
      EVENT.pack(0,EVENT_CONTROL,enc(0,0),122,1,1.0,80.,*lo),
      EVENT.pack(0,EVENT_CONTROL,enc(0,0),0,1,0.,80.,*lo),
      EVENT.pack(1000,EVENT_NOTE_ON,enc(0,0),72,1,.8,80.,*lo),
      EVENT.pack(6000,EVENT_CONTROL,enc(0,0),0,1,0.,80.,*hi),
      EVENT.pack(end-1,EVENT_NOTE_OFF,enc(0,0),72,1,0.,80.,*hi),
      EVENT.pack(end,EVENT_CONTROL,enc(0,0),122,1,0.,80.,*hi),
    ]
    h=RequestHeader(TYPE_RENDER,4501,0,end,sr,len(ev),4,1,80.,.35,(1<<7)|(1<<25))
    with socket.create_connection(('127.0.0.1',a.port),timeout=5) as s:
        s.sendall(pack_request_header(h)+b''.join(ev));rh=unpack_response_header(recv_exact(s,RESP_HEADER.size));payload=recv_exact(s,rh.payload_bytes)
    assert rh.status in (STATUS_OK,STATUS_CACHE_HIT) and rh.frames==end and rh.channels==34 and len(payload)==end*34*4
    print('SONICRAFT v4.5 gesture service protocol PASS',rh.frames,rh.channels)
if __name__=='__main__':main()
