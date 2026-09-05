from __future__ import annotations
import argparse,socket
from protocol import *
def request(port,reserved):
    sr=48000;start=100000;end=start+sr//4;ctrl=[.65,.5,.9,.86,.5,1,1,.18,.5,0,.5,.5,.38,0.]
    ev=[EVENT.pack(start,EVENT_NOTE_ON,0,69,0,.8,68.,*ctrl),EVENT.pack(end-10,EVENT_NOTE_OFF,0,69,0,0.,68.,*ctrl)]
    h=RequestHeader(TYPE_JUDGE,381,start,end,sr,len(ev),4,1,68.,.35,(1<<7)|(2<<8)|(10<<21)|(1<<26))
    with socket.create_connection(('127.0.0.1',port),timeout=5) as s:
        s.sendall(pack_request_header(h)+JUDGE_CONFIG.pack(.37,0,0,reserved)+b''.join(ev));rh=unpack_response_header(recv_exact(s,RESP_HEADER.size));payload=recv_exact(s,rh.payload_bytes)
    return rh,payload

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
    # legacy v3.7 wire size stays 100 bytes
    rh,p=request(a.port,0);assert len(p)==JUDGE_RESULT.size==100;assert JUDGE_RESULT.unpack(p)[0]==1
    # v3.8 gets 144-byte personalized result
    rh,p=request(a.port,JUDGE_CAP_PERSONAL|JUDGE_PERSONAL_ENABLED|255);un=JUDGE_RESULT_V2.unpack(p);v,winner,valid=un[:3];vals=list(un[3:-1]);profile_hash32=un[-1];assert len(p)==144 and v==2 and valid==15 and len(vals)==34 and profile_hash32>=0
    # Query / learn / restart-persistent payload path
    with socket.create_connection(('127.0.0.1',a.port),timeout=5) as s:
        h=RequestHeader(TYPE_PREFERENCE,382,0,0,48000,0,0,0,68.,0.,0);metrics=vals[:24]
        s.sendall(pack_request_header(h)+PREFERENCE_EVENT.pack(3,1,0,*metrics));pr=unpack_response_header(recv_exact(s,RESP_HEADER.size));profile=PROFILE_RESULT.unpack(recv_exact(s,pr.payload_bytes))
    assert profile[0]==1 and profile[4]>=1.35
    print('SONICRAFT v3.8 personal protocol PASS legacy=100 personal=144 evidence=',round(profile[4],3))
if __name__=='__main__':main()
