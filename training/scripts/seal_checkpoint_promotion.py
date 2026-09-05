from __future__ import annotations
import argparse,hashlib,json,torch
from pathlib import Path
CURRICULUM='lane_locked_acoustic_promotion_v20'

def tensor_digest(ck:dict)->str:
    h=hashlib.sha256()
    for root in ('model','ema','decoder'):
        sd=ck.get(root)
        if not isinstance(sd,dict):continue
        for k in sorted(sd):
            v=sd[k];h.update(root.encode());h.update(k.encode())
            if torch.is_tensor(v):h.update(v.detach().cpu().contiguous().numpy().tobytes())
            else:h.update(repr(v).encode())
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--checkpoint',required=True);ap.add_argument('--promotion',required=True);ap.add_argument('--out');a=ap.parse_args()
    pp=Path(a.promotion);pr=json.loads(pp.read_text(encoding='utf-8'));pid=str(pr.get('promotion_id',''))
    if int(pr.get('schema',0))!=1 or pr.get('promotion_version')!='acoustic_promotion_v20' or not pr.get('promotion_pass') or len(pid)!=64:raise SystemExit('promotion report has not passed v2.0')
    src=Path(a.checkpoint);ck=torch.load(src,map_location='cpu',weights_only=False)
    if not isinstance(ck,dict):raise SystemExit('checkpoint must be a metadata dict')
    mix=dict(ck.get('training_mix') or {})
    if abs(float(mix.get('real',-1))-.8)>1e-6 or abs(float(mix.get('modeled',-1))-.2)>1e-6 or str(mix.get('curriculum'))!=CURRICULUM:raise SystemExit('checkpoint is not a v2.0 REAL80/MODEL20 candidate')
    before=tensor_digest(ck);existing=ck.get('acoustic_promotion_id')
    if existing not in (None,'',pid):raise SystemExit('checkpoint already bound to a different promotion')
    ck['acoustic_promotion_id']=pid;ck['acoustic_promotion_seal']={'schema':1,'promotion_id':pid,'tensor_sha256':before,'promotion_evidence':pp.name}
    out=Path(a.out) if a.out else src;out.parent.mkdir(parents=True,exist_ok=True);torch.save(ck,out)
    verify=torch.load(out,map_location='cpu',weights_only=False);after=tensor_digest(verify)
    if before!=after:raise SystemExit('tensor digest changed while sealing promotion')
    print('SEALED',out,'promotion',pid,'tensor_sha256',after)
if __name__=='__main__':main()
