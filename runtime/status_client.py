from __future__ import annotations
import argparse,socket
from protocol import *
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=49337);a=ap.parse_args()
 h=RequestHeader(TYPE_PING,1,0,0,48000,0,4,0,68.,0.,0)
 try:
  with socket.create_connection(('127.0.0.1',a.port),timeout=1.5) as s:
   s.sendall(pack_request_header(h));r=unpack_response_header(recv_exact(s,RESP_HEADER.size))
  backend='ORT' if (r.flags&(1<<1)) else ('TORCH' if (r.flags&(1<<2)) else ('MOCK' if (r.flags&(1<<3)) else 'UNKNOWN'))
  if r.status==STATUS_OK: print('READY:'+backend);return 0
  if r.status==STATUS_MODEL_NOT_READY: print('SERVICE_ONLINE_MODEL_NOT_READY:'+backend);return 2
  print('SERVICE_ERROR',r.status,backend);return 3
 except Exception as e:
  print('OFFLINE',type(e).__name__,e);return 1
if __name__=='__main__': raise SystemExit(main())
