#!/usr/bin/env python3
from __future__ import annotations
"""Bind a passed transition-promotion report to the exact candidate checkpoint.

Only checkpoint metadata is changed. Tensor bytes are hashed before/after and the
operation fails if model tensors move.
"""
import argparse, hashlib, json
from pathlib import Path
import torch


def tensor_digest(ck:dict)->str:
    h=hashlib.sha256()
    for root in ('model','ema','decoder'):
        sd=ck.get(root)
        if not isinstance(sd,dict): continue
        for k in sorted(sd):
            v=sd[k];h.update(root.encode());h.update(k.encode())
            if torch.is_tensor(v): h.update(v.detach().cpu().contiguous().numpy().tobytes())
            else: h.update(repr(v).encode())
    return h.hexdigest()


def file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--checkpoint',required=True);ap.add_argument('--promotion',required=True);ap.add_argument('--curriculum',required=True);ap.add_argument('--out');a=ap.parse_args()
    pp=Path(a.promotion);pr=json.loads(pp.read_text(encoding='utf-8'));pid=str(pr.get('promotion_id',''))
    if int(pr.get('schema',0))!=1 or pr.get('promotion_version')!='transition_promotion_v1' or not pr.get('promotion_pass') or len(pid)!=64:
        raise SystemExit('transition promotion report has not passed v1 contract')
    src=Path(a.checkpoint);candidate_sha=file_sha(src)
    if candidate_sha!=str(pr.get('candidate_checkpoint_sha256','')).lower():
        raise SystemExit('promotion report does not target this checkpoint file')
    cp=Path(a.curriculum);cr=json.loads(cp.read_text(encoding='utf-8'))
    if cr.get('version')!='phrase_finetune_index_v1' or not cr.get('curriculum_sweep'):
        raise SystemExit('invalid phrase curriculum report')
    ck=torch.load(src,map_location='cpu',weights_only=False)
    if not isinstance(ck,dict): raise SystemExit('checkpoint must be a metadata dict')
    before=tensor_digest(ck)
    existing=ck.get('transition_promotion_id')
    if existing not in (None,'',pid): raise SystemExit('checkpoint already bound to another transition promotion')
    ck['transition_promotion_id']=pid
    ck['transition_promotion_seal']={
        'schema':1,'promotion_id':pid,'tensor_sha256':before,'promotion_evidence':pp.name,
        'curriculum_evidence':cp.name,'curriculum_sha256':file_sha(cp),
        'heldout_index_sha256':pr.get('heldout_index_sha256'),
    }
    out=Path(a.out) if a.out else src;out.parent.mkdir(parents=True,exist_ok=True);torch.save(ck,out)
    verify=torch.load(out,map_location='cpu',weights_only=False);after=tensor_digest(verify)
    if before!=after: raise SystemExit('tensor digest changed while sealing transition promotion')
    print('TRANSITION SEALED',out,'promotion',pid,'tensor_sha256',after)

if __name__=='__main__':main()
