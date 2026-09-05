#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataclasses import replace
from cleanroom_bowed_synth import ARTICULATIONS, random_controls, synthesize, synthesize_section
import numpy as np

def main():
    ap=argparse.ArgumentParser(description='Generate SONICRAFT-owned physical bowed-string teacher data. No proprietary audio/assets are used.')
    ap.add_argument('--out',default='datasets/generated/cleanroom_bowed_v18')
    ap.add_argument('--count',type=int,default=1200); ap.add_argument('--seconds',type=float,default=2.0)
    ap.add_argument('--sample-rate',type=int,default=48000); ap.add_argument('--seed',type=int,default=1808)
    ap.add_argument('--section-prob',type=float,default=.65,help='Fraction of modeled clips rendered as independent 2-8 player sections.')
    ap.add_argument('--max-players',type=int,default=8)
    a=ap.parse_args(); root=Path(a.out); audio=root/'audio'; audio.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(a.seed); rows=[]
    for i in range(a.count):
        # Round-robin articulation first, then randomize the other controls. This guarantees scarce-technique coverage.
        art=i%len(ARTICULATIONS); inst=(i//len(ARTICULATIONS))%4
        c=random_controls(rng,inst,art)
        if rng.random()<a.section_prob:
            players=int(rng.integers(2,max(3,a.max_players+1)))
            c=replace(c,section_players=players,section_pitch_spread_cents=float(rng.uniform(2.0,10.0)),
                      section_timing_spread_ms=float(rng.uniform(2.0,18.0)),section_bow_spread=float(rng.uniform(.035,.16)))
            wav=synthesize_section(c,a.seconds,a.sample_rate,a.seed+i)
        else:
            wav=synthesize(c,a.seconds,a.sample_rate,a.seed+i)
        p=audio/f'{i:06d}.wav'; sf.write(p,wav,a.sample_rate,subtype='PCM_24')
        row=c.manifest(); row.update({
            'audio':str(p.resolve()),'dataset':'synthetic_cleanroom_bowed_v18','release_blocked':False,
            'commercial_safe':True,'sample_rate':a.sample_rate,'seconds':a.seconds,
            'dynamics':c.bow_speed,'expression':c.bow_speed,'vibrato':min(1.0,c.vibrato_depth_cents/60.0),
            'legato':1.0 if art in (1,2,3) else 0.0,'pitchbend':c.slide_semitones/12.0 if art==2 else 0.0,
            'transition_speed':max(.05,min(.95,1.0-c.slide_time)),'short_tightness':.82 if art in (5,6) else .45,
            'attack_character':min(1.0,.35+.45*c.bow_force),'phrase_position':.5,'prev_interval':.5,'next_interval':.5,
            'bow_change_prob':.85 if art==7 else .25,'tempo_bpm':68.0,'note_duration_beats':2.0,
            'dynamics_known':1.0,'vibrato_known':1.0,'vibrato_physics_known':1.0,'expression_known':1.0,
            'legato_known':1.0,'pitchbend_known':1.0 if art==2 else 0.0,'timing_known':1.0,'articulation_known':1.0,
            'player':int(i%8),'ensemble_kind':'section' if c.section_players>1 else 'solo',
            'section_players':int(c.section_players)
        }); rows.append(row)
    idx=root/'index.jsonl'; idx.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows),encoding='utf-8')
    print('generated',len(rows),'clean-room bowed clips ->',idx)
    sec=sum(int(r.get('section_players',1))>1 for r in rows)
    print('section teacher clips',sec,'/',len(rows),'max_players',a.max_players)
    print('policy: training_origin=modeled; final_timbre_anchor=false; intended sampler mass=0.20')
if __name__=='__main__': main()
