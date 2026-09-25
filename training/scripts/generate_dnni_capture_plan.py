#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

RANGES = {0:(55,96),1:(55,93),2:(48,84),3:(36,72)}
ARTS = ["sustain","legato","portamento","expressive_long","marcato","staccato","spiccato","tremolo","pizzicato","trill","harmonic","flautando"]


def pitches(lo, hi, n):
    if n <= 1: return [(lo+hi)//2]
    vals = [round(lo + i*(hi-lo)/(n-1)) for i in range(n)]
    return sorted(set(int(x) for x in vals))


def main():
    ap=argparse.ArgumentParser(description="Create a deterministic four-timbre audio-capture plan for SONICRAFT research training.")
    ap.add_argument('--out',default='datasets/dnni_four_timbres/capture_plan.jsonl')
    ap.add_argument('--pitches-per-timbre',type=int,default=5)
    ap.add_argument('--velocities',default='0.45,0.70,0.95')
    ap.add_argument('--seconds',type=float,default=2.0)
    a=ap.parse_args(); velocities=[float(x) for x in a.velocities.split(',')]
    rows=[]
    for inst in range(4):
        lo,hi=RANGES[inst]
        for art,art_name in enumerate(ARTS):
            for pitch in pitches(lo,hi,a.pitches_per_timbre):
                for vel in velocities:
                    tag=f"t{inst+1}_i{inst}_a{art:02d}_p{pitch:03d}_v{int(round(vel*100)):03d}"
                    rows.append({
                        'capture_id':tag,'timbre_id':f'timbre_{inst+1}','instrument':inst,
                        'articulation':art,'articulation_name':art_name,'pitch':pitch,'velocity':vel,
                        'seconds':a.seconds,'expected_wav':f"rendered/timbre_{inst+1}/{tag}.wav"
                    })
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    print('capture rows',len(rows),'->',p)
    print('Render each row with its matching DNNI timbre and keep the exact expected filename.')

if __name__=='__main__':main()
