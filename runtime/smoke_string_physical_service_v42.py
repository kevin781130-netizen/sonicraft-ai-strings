from __future__ import annotations
import argparse,socket
from protocol import *
def enc(part,lane):return (part&3)|((lane+1)<<2)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
    sr=48000;end=12000
    c=[.62,.5,.9,.86,.5,1,1,.18,.5,1/11,.5,.5,.38,0.]
    part=enc(0,0)
    physical=[(112,.67),(113,.50),(114,0.),(115,1.),(116,.75),(117,.70),(118,.60),(119,.33)]
    ev=[EVENT.pack(0,EVENT_CONTROL,part,code,1,val,80.,*c) for code,val in physical]
    ev += [EVENT.pack(0,EVENT_NOTE_ON,part,72,1,.8,80.,*c),EVENT.pack(end-1,EVENT_NOTE_OFF,part,72,1,0.,80.,*c)]
    flags=(1<<7)|(1<<25)
    h=RequestHeader(TYPE_RENDER,4201,0,end,sr,len(ev),4,1,80.,.35,flags)
    with socket.create_connection(('127.0.0.1',a.port),timeout=5) as s:
        s.sendall(pack_request_header(h)+b''.join(ev));rh=unpack_response_header(recv_exact(s,RESP_HEADER.size));payload=recv_exact(s,rh.payload_bytes)
    assert rh.status in (STATUS_OK,STATUS_CACHE_HIT)
    assert rh.frames==end and rh.channels==34 and len(payload)==end*34*4
    print('SONICRAFT v4.2 physical String Voice service protocol PASS',rh.frames,rh.channels)
if __name__=='__main__':main()
