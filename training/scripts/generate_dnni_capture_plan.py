#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

ARTS = ["sustain","legato","portamento","expressive_long","marcato","staccato","spiccato","tremolo","pizzicato","trill","harmonic","flautando"]


def pitches(lo, hi, n):
    if n <= 1: return [(lo+hi)//2]
    vals = [round(lo + i*(hi-lo)/(n-1)) for i in range(n)]
    return sorted(set(int(x) for x in vals))


def main():
    ap=argparse.ArgumentParser(description="Create a deterministic four-timbre audio-capture plan for SONICRAFT research training.")
    ap.add_argument('--out',default='datasets/dnni_four_timbres/capture_plan.jsonl')
    ap.add_argument('--config',default='training/configs/dnni_four_timbres.json')
    ap.add_argument('--pitches-per-timbre',type=int,default=5)
    ap.add_argument('--velocities',default='0.45,0.70,0.95')
    ap.add_argument('--seconds',type=float,default=2.0)
    a=ap.parse_args(); velocities=[float(x) for x in a.velocities.split(',')]
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    slots=sorted(cfg.get('slots',[]),key=lambda x:int(x.get('slot',0)))
    if len(slots)!=4: raise SystemExit(f'{a.config}: expected exactly four slots')
    rows=[]
    for slot in slots:
        inst=int(slot['instrument']);lo=int(slot['midi_low']);hi=int(slot['midi_high'])
        tid=str(slot['timbre_id']);label=str(slot.get('label',tid))
        for art,art_name in enumerate(ARTS):
            for pitch in pitches(lo,hi,a.pitches_per_timbre):
                for vel in velocities:
                    tag=f"s{int(slot['slot'])}_i{inst}_a{art:02d}_p{pitch:03d}_v{int(round(vel*100)):03d}"
                    rows.append({
                        'capture_id':tag,'timbre_id':tid,'timbre_label':label,'instrument':inst,
                        'articulation':art,'articulation_name':art_name,'articulation_verified':False,'pitch':pitch,'velocity':vel,
                        'seconds':a.seconds,'expected_wav':f"rendered/{tid}/{tag}.wav"
                    })
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    print('capture rows',len(rows),'->',p)
    print('Render each row with its matching DNNI timbre and keep the exact expected filename.')

if __name__=='__main__':main()
