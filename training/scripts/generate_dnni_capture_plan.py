#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

ARTS = ["sustain","legato","portamento","expressive_long","marcato","staccato","spiccato","tremolo","pizzicato","trill","harmonic","flautando"]

def pitches(lo, hi, n):
    if n <= 1: return [(lo+hi)//2]
    vals=[round(lo+i*(hi-lo)/(n-1)) for i in range(n)]
    return sorted(set(int(x) for x in vals))

def parse_articulations(text):
    if str(text).strip().lower()=="all": return list(range(len(ARTS)))
    out=sorted(set(int(x.strip()) for x in str(text).split(",") if x.strip()))
    if not out or any(x<0 or x>=len(ARTS) for x in out):
        raise ValueError(f"articulations must be 0..{len(ARTS)-1}, comma-separated, or 'all'")
    return out

def main():
    ap=argparse.ArgumentParser(description="Create a deterministic four-timbre capture plan. Defaults are timbre-only, not fabricated articulation supervision.")
    ap.add_argument('--out',default='datasets/dnni_four_timbres/capture_plan.jsonl')
    ap.add_argument('--config',default='training/configs/dnni_four_timbres.json')
    ap.add_argument('--pitches-per-timbre',type=int,default=16,
                    help='Evenly sample the configured MIDI range; default 16 per timbre.')
    ap.add_argument('--velocities',default='0.70',
                    help='Comma-separated MIDI velocity fractions. Default is neutral 0.70.')
    ap.add_argument('--articulations',default='0',
                    help='Articulation IDs to capture; default 0 only. Use "all" only when the source really renders distinct articulations.')
    ap.add_argument('--articulation-verified',action='store_true',
                    help='Mark requested articulation IDs as semantically verified. Off by default.')
    ap.add_argument('--velocity-verified',action='store_true',
                    help='Mark MIDI velocity as meaningful target conditioning. Off by default.')
    ap.add_argument('--seconds',type=float,default=2.0)
    a=ap.parse_args()
    velocities=[float(x) for x in a.velocities.split(',') if x.strip()]
    if not velocities or any(v<=0 or v>1 for v in velocities): raise SystemExit('velocities must be in (0,1]')
    arts=parse_articulations(a.articulations)
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'))
    slots=sorted(cfg.get('slots',[]),key=lambda x:int(x.get('slot',0)))
    if len(slots)!=4: raise SystemExit(f'{a.config}: expected exactly four slots')
    rows=[]
    for slot in slots:
        inst=int(slot['instrument']);lo=int(slot['midi_low']);hi=int(slot['midi_high'])
        tid=str(slot['timbre_id']);label=str(slot.get('label',tid))
        for art in arts:
            art_name=ARTS[art]
            for pitch in pitches(lo,hi,a.pitches_per_timbre):
                for vel in velocities:
                    tag=f"s{int(slot['slot'])}_i{inst}_a{art:02d}_p{pitch:03d}_v{int(round(vel*100)):03d}"
                    rows.append({
                        'capture_id':tag,'timbre_id':tid,'timbre_label':label,'instrument':inst,
                        'articulation':art,'articulation_name':art_name,'articulation_verified':bool(a.articulation_verified),
                        'pitch':pitch,'velocity':vel,'velocity_verified':bool(a.velocity_verified),
                        'seconds':a.seconds,'expected_wav':f"rendered/{tid}/{tag}.wav"
                    })
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    print('capture rows',len(rows),'->',p)
    print('mode:',len(arts),'articulation lane(s),',len(velocities),'velocity lane(s),',a.pitches_per_timbre,'pitch target(s) per timbre')
    if not a.articulation_verified:
        print('articulation supervision: UNVERIFIED / timbre-only')
    if not a.velocity_verified:
        print('velocity supervision: UNVERIFIED / neutral conditioning in training manifest')
    print('Render each row with its matching DNNI timbre and keep the exact expected filename.')

if __name__=='__main__':main()
