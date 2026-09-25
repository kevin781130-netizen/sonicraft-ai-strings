#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description="Run a command while teeing combined stdout/stderr to a persistent log.")
    ap.add_argument("--log",required=True)
    ap.add_argument("command",nargs=argparse.REMAINDER)
    a=ap.parse_args()
    cmd=list(a.command)
    if cmd and cmd[0]=="--": cmd=cmd[1:]
    if not cmd: raise SystemExit("no command supplied")
    p=Path(a.log); p.parent.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with p.open("a",encoding="utf-8",errors="replace") as log:
        header=f"\n===== {stamp} START {' '.join(cmd)} =====\n"
        sys.stdout.write(header); log.write(header); log.flush()
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,errors="replace")
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line); sys.stdout.flush()
            log.write(line); log.flush()
        rc=proc.wait()
        end=f"===== {dt.datetime.now().astimezone().isoformat(timespec='seconds')} END rc={rc} =====\n"
        sys.stdout.write(end); log.write(end); log.flush()
        raise SystemExit(rc)

if __name__=="__main__":
    main()
