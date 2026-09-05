#!/usr/bin/env python3
"""Compare Python/service reference tensors with the C++ in-process engine fixtures.

Manifest JSON format:
{"pairs":[{"scenario":"manual","reference":"ref_manual.npz","native":"native_manual.npz"}, ...]}
Required NPZ arrays: raw_controls, frontier_context, renderer_velocity, decoder_audio, stage_audio.
This gate is intentionally strict and is not expected to pass before production checkpoint parity work.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
REQUIRED_SCENARIOS={'manual','assist','polyphony','q4_phrase','retake','multiout'}
AUTHORITY_RAW=(0,1,2,3,5,6,7,8,27,28,29,30,32) # pitch/gate/onset/velocity + explicit authored lanes/known flags

def metric(a,b):
    a=np.asarray(a,np.float64);b=np.asarray(b,np.float64)
    if a.shape!=b.shape:return {'shape_match':False,'max_abs':1e9,'rmse':1e9,'corr':-1.0}
    d=a-b;rm=float(np.sqrt(np.mean(d*d))) if d.size else 0.;mx=float(np.max(np.abs(d))) if d.size else 0.
    aa=a.reshape(-1);bb=b.reshape(-1)
    corr=1.0 if aa.size<2 or (np.std(aa)<1e-12 and np.std(bb)<1e-12 and mx<1e-12) else (float(np.corrcoef(aa,bb)[0,1]) if np.std(aa)>1e-12 and np.std(bb)>1e-12 else 0.0)
    return {'shape_match':True,'max_abs':mx,'rmse':rm,'corr':corr}
def ev(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();mp=Path(a.manifest);m=json.loads(mp.read_text());rows=[];reasons=[];seen=set()
    for ent in m.get('pairs',[]):
        sc=str(ent.get('scenario',''));seen.add(sc);rp=(mp.parent/ent['reference']).resolve();npth=(mp.parent/ent['native']).resolve();r=np.load(rp);n=np.load(npth);miss=[k for k in ('raw_controls','frontier_context','renderer_velocity','decoder_audio','stage_audio') if k not in r or k not in n]
        if miss:reasons.append(sc+':missing:'+','.join(miss));continue
        rr=np.asarray(r['raw_controls']);nn=np.asarray(n['raw_controls']);auth=metric(rr[...,list(AUTHORITY_RAW)],nn[...,list(AUTHORITY_RAW)]) if rr.ndim>=2 and rr.shape[-1]>=33 and nn.shape==rr.shape else {'shape_match':False,'max_abs':1e9,'rmse':1e9,'corr':-1}
        row={'scenario':sc,'authority':auth,'raw':metric(rr,nn),'frontier':metric(r['frontier_context'],n['frontier_context']),'renderer':metric(r['renderer_velocity'],n['renderer_velocity']),'decoder':metric(r['decoder_audio'],n['decoder_audio']),'stage':metric(r['stage_audio'],n['stage_audio'])};rows.append(row)
        if not auth['shape_match'] or auth['max_abs']>1e-6:reasons.append(sc+':midi_authority_parity')
        # Hidden controls may differ slightly in implementation; model tensors/audio may not.
        if not row['frontier']['shape_match'] or row['frontier']['rmse']>2e-4:reasons.append(sc+':frontier_context_parity')
        if not row['renderer']['shape_match'] or row['renderer']['rmse']>2e-5 or row['renderer']['max_abs']>2e-4:reasons.append(sc+':renderer_tensor_parity')
        if not row['decoder']['shape_match'] or row['decoder']['rmse']>3e-5 or row['decoder']['corr']<0.99999:reasons.append(sc+':decoder_parity')
        if not row['stage']['shape_match'] or row['stage']['rmse']>5e-5 or row['stage']['corr']<0.99995:reasons.append(sc+':stage_parity')
    missing=sorted(REQUIRED_SCENARIOS-seen)
    if missing:reasons.append('missing_scenarios:'+','.join(missing))
    rep={'schema':1,'kind':'sonicraft_inprocess_parity_v26','pair_count':len(rows),'required_scenarios':sorted(REQUIRED_SCENARIOS),'scenarios':rows,'reasons':reasons,'passed':not reasons};rep['evidence_id']=ev(rep);Path(a.out).write_text(json.dumps(rep,indent=2),encoding='utf-8');print('INPROCESS PARITY V26','PASS' if rep['passed'] else 'FAIL','pairs',len(rows),reasons[:6])
    if reasons:raise SystemExit(3)
if __name__=='__main__':main()
