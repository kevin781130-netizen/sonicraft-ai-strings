#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path


def sha256(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''): h.update(b)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description='Turn four DNNI timbre capture WAVs into a SONICRAFT research manifest.')
    ap.add_argument('--plan',default='datasets/dnni_four_timbres/capture_plan.jsonl')
    ap.add_argument('--root',default='datasets/dnni_four_timbres')
    ap.add_argument('--out',default='datasets/dnni_four_timbres/rendered/index.jsonl')
    ap.add_argument('--allow-missing',action='store_true')
    a=ap.parse_args(); root=Path(a.root); rows=[]; missing=[]
    plan=[json.loads(x) for x in Path(a.plan).read_text(encoding='utf-8').splitlines() if x.strip()]
    for i,r in enumerate(plan):
        wav=root/r['expected_wav']
        if not wav.exists():
            missing.append(str(wav)); continue
        vel=float(r['velocity']); art=int(r['articulation']); art_verified=bool(r.get('articulation_verified',False))
        rows.append({
            'audio':str(wav.resolve()), 'dataset':f"dnni_research_{r['timbre_id']}",
            'training_origin':'real', 'source_kind':'proprietary_teacher_render_research_only',
            'release_blocked':True, 'commercial_safe':False, 'cleanroom_eligible':False,
            'dnni_timbre_id':r['timbre_id'], 'capture_id':r['capture_id'], 'audio_sha256':sha256(wav),
            'instrument':int(r['instrument']), 'articulation':art, 'pitch':float(r['pitch']), 'player':int(r['instrument']),
            'velocity':vel, 'dynamics':vel, 'expression':vel,
            'vibrato':0.0, 'legato':0.0, 'pitchbend':0.0,
            'transition_speed':0.5, 'short_tightness':0.5, 'attack_character':0.5,
            'phrase_position':0.5, 'prev_interval':0.5, 'next_interval':0.5,
            'bow_change_prob':0.0, 'tempo_bpm':68.0, 'note_duration_beats':2.0,
            'dynamics_known':0.0, 'vibrato_known':0.0, 'vibrato_physics_known':0.0, 'expression_known':0.0,
            'legato_known':1.0 if art_verified and art in (1,2,3) else 0.0,
            'pitchbend_known':1.0 if art_verified and art==2 else 0.0,
            'timing_known':1.0, 'articulation_known':1.0 if art_verified else 0.0,
            'articulation_verified':art_verified,
        })
    if missing and not a.allow_missing:
        sample='\n  '.join(missing[:20]); raise SystemExit(f'missing {len(missing)} capture WAVs; first paths:\n  {sample}')
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    print('research render rows',len(rows),'missing',len(missing),'->',p)
    if missing: print('WARNING: partial capture manifest; release remains blocked.')

if __name__=='__main__':main()
