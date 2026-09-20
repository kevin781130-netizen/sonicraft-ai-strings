#!/usr/bin/env python3
from __future__ import annotations
"""Deterministic latent-space transition evaluation for renderer checkpoints.

Use the same held-out phrase latent index and seed for baseline and candidate.
The metric intentionally measures the renderer's learned transition field, not
physical-teacher audio similarity, so modeled data remains a transition teacher
rather than a final timbre target.
"""
import argparse, hashlib, json, sys
from collections import defaultdict
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.ballad_flow_renderer import BalladFlowRenderer
from train_ballad_renderer import Segments, collate, run_batch

SCHEMA=1
VERSION='renderer_transition_eval_v1'


def sha256(path: str|Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_model(path,dev):
    ck=torch.load(path,map_location='cpu',weights_only=False)
    cfg=dict(ck.get('config') or {})
    latent_ch=int(ck.get('latent_ch') or 0)
    if latent_ch<=0:
        sd=ck.get('ema') or ck.get('model') or {}
        # All current renderers expose input/output projections; fail clearly if
        # an old checkpoint lacks geometry metadata rather than guessing silently.
        for k,v in sd.items():
            if torch.is_tensor(v) and k.endswith('out.weight') and v.ndim>=2:
                latent_ch=int(v.shape[0]); break
    if latent_ch<=0: raise RuntimeError('checkpoint has no usable latent_ch metadata')
    model=BalladFlowRenderer(latent_ch=latent_ch,**cfg).to(dev).eval()
    model.load_state_dict(ck.get('ema',ck.get('model')),strict=True)
    return model,ck


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--checkpoint',required=True);ap.add_argument('--index',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--batch',type=int,default=4);ap.add_argument('--seed',type=int,default=260917)
    ap.add_argument('--max-samples',type=int,default=0,help='0 = all held-out rows')
    a=ap.parse_args(); dev='cuda' if torch.cuda.is_available() else 'cpu'
    ds=Segments(a.index)
    phrase_rows=[i for i,r in enumerate(ds.rows) if str(r.get('phrase_family') or '').strip()]
    if not phrase_rows: raise SystemExit('held-out index contains no phrase_family rows')
    if a.max_samples>0: phrase_rows=phrase_rows[:a.max_samples]
    sub=Subset(ds,phrase_rows);dl=DataLoader(sub,batch_size=a.batch,shuffle=False,num_workers=0,collate_fn=collate)
    model,ck=load_model(a.checkpoint,dev)

    sums=defaultdict(float);batches=0;samples=0
    with torch.no_grad():
        for bi,batch in enumerate(dl):
            # run_batch samples diffusion time/noise internally; resetting the
            # seed per batch makes baseline/candidate comparisons paired.
            torch.manual_seed(a.seed+bi)
            if torch.cuda.is_available(): torch.cuda.manual_seed_all(a.seed+bi)
            loss,m=run_batch(model,batch,dev,train=False,cond_dropout=0.0,modeled_sources=set(),modeled_flow_weight=1.0)
            bs=int(batch[0].shape[0]);samples+=bs;batches+=1
            sums['loss']+=float(loss)*bs
            for k in ('flow','continuity','accel'): sums[k]+=float(m[k])*bs
    metrics={k:v/max(1,samples) for k,v in sums.items()}
    report={
        'schema':SCHEMA,'version':VERSION,'checkpoint_sha256':sha256(a.checkpoint),'index_sha256':sha256(a.index),
        'sample_count':samples,'batch_count':batches,'seed':a.seed,'metrics':metrics,
        'checkpoint_training_mix':ck.get('training_mix'),'codec_kind':ck.get('codec_kind'),'latent_ch':ck.get('latent_ch'),
        'interpretation':'lower is better; continuity/accel are transition-field errors on paired held-out phrase latents',
    }
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=='__main__':main()
