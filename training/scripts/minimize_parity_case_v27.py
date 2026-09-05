#!/usr/bin/env python3
"""Delta-debug an event case using an external replay command.
The replay command receives {case} and must exit 3 while the divergence reproduces.
"""
from __future__ import annotations
import argparse,json,shlex,subprocess,tempfile
from pathlib import Path

def reproduces(events,base,cmd):
 d=dict(base);d['events']=events
 with tempfile.NamedTemporaryFile('w',suffix='.json',delete=False,encoding='utf-8') as f:json.dump(d,f);p=f.name
 try:return subprocess.run(cmd.replace('{case}',shlex.quote(p)),shell=True).returncode==3
 finally:Path(p).unlink(missing_ok=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--case',required=True);ap.add_argument('--replay-cmd',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();d=json.loads(Path(a.case).read_text());ev=list(d.get('events',[]));base={k:v for k,v in d.items() if k!='events'}
 if not reproduces(ev,base,a.replay_cmd):raise SystemExit('case does not reproduce divergence')
 gran=2
 while len(ev)>1:
  chunk=max(1,(len(ev)+gran-1)//gran);changed=False
  for i in range(0,len(ev),chunk):
   cand=ev[:i]+ev[i+chunk:]
   if cand and reproduces(cand,base,a.replay_cmd):ev=cand;gran=max(2,gran-1);changed=True;break
  if not changed:
   if gran>=len(ev):break
   gran=min(len(ev),gran*2)
 out=dict(base);out['events']=ev;Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf-8');print('PARITY MINIMIZER',len(d.get('events',[])),'->',len(ev))
if __name__=='__main__':main()
