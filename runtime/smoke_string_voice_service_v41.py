from __future__ import annotations
import argparse,socket
from protocol import *
def enc(part,lane):return (part&3)|((lane+1)<<2)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
    sr=48000;end=12000
    ca=[.42,.35,.9,.86,.5,1,1,.18,.5,7/11,.35,.5,.72,0.]
    cb=[.84,.70,.9,.86,.5,1,1,.18,.5,0,.66,.5,.20,0.]
    ev=[
      EVENT.pack(0,EVENT_CONTROL,enc(0,0),0,(1<<4)|7,0.,80.,*ca),
      EVENT.pack(0,EVENT_NOTE_ON,enc(0,0),72,(1<<4)|7,.8,80.,*ca),
      EVENT.pack(end-1,EVENT_NOTE_OFF,enc(0,0),72,(1<<4)|7,0.,80.,*ca),
      EVENT.pack(0,EVENT_CONTROL,enc(0,4),0,(4<<4)|0,0.,80.,*cb),
      EVENT.pack(0,EVENT_NOTE_ON,enc(0,4),76,(4<<4)|0,.8,80.,*cb),
      EVENT.pack(end-1,EVENT_NOTE_OFF,enc(0,4),76,(4<<4)|0,0.,80.,*cb),
    ]
    flags=(1<<7)|(1<<25)
    h=RequestHeader(TYPE_RENDER,4101,0,end,sr,len(ev),4,1,80.,.35,flags)
    with socket.create_connection(('127.0.0.1',a.port),timeout=5) as s:
        s.sendall(pack_request_header(h)+b''.join(ev))
        rh=unpack_response_header(recv_exact(s,RESP_HEADER.size))
        payload=recv_exact(s,rh.payload_bytes)
    assert rh.status in (STATUS_OK,STATUS_CACHE_HIT)
    assert rh.frames==end and rh.channels==34 and len(payload)==end*34*4,(rh.frames,rh.channels,len(payload))
    print('SONICRAFT v4.1 encoded String Voice service protocol PASS',rh.frames,rh.channels)
if __name__=='__main__':main()
