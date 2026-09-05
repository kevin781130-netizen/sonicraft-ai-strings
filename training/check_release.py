from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('index'); a=ap.parse_args(); blocked=[]
    for line in Path(a.index).read_text().splitlines():
        if not line.strip():continue
        r=json.loads(line)
        if r.get('release_blocked'):blocked.append(r)
    if blocked:
        print(f'RELEASE BLOCKED: {len(blocked)} training items do not have approved commercial provenance.'); sys.exit(2)
    print('release provenance gate: PASS')
if __name__=='__main__':main()
