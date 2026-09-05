from __future__ import annotations
import argparse, json, random, sys
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from models.vibrato_expert import VibratoControlExpert
from source_policy import validate_index

class VibDataset(Dataset):
    def __init__(self,index):
        self.rows=[json.loads(x) for x in Path(index).read_text(encoding='utf-8').splitlines() if x.strip()]
    def __len__(self): return len(self.rows)
    def __getitem__(self,i):
        r=self.rows[i]; d=np.load(r['file'])
        n=len(d['pitch'])
        def arr(k,default): return torch.from_numpy((d[k] if k in d.files else np.full(n,default,np.float32)).astype('float32'))
        # physical labels are only valid where vibrato_known=1
        return (arr('vibrato',0),arr('dynamics',.6),arr('pitch',69),arr('note_progress',.5),arr('phrase_position',.5),
                arr('tempo_bpm',68),arr('note_duration_beats',2),arr('speed_profile',0),torch.tensor(int(d['instrument'])),
                arr('vibrato_depth_cents',0)/100.0,arr('vibrato_rate_hz',5.2)/10.0,
                arr('vibrato_onset_ms',250)/1000.0,arr('vibrato_jitter',.03),
                arr('vibrato_depth_known',0) if 'vibrato_depth_known' in d.files else arr('vibrato_known',0),
                arr('vibrato_rate_known',0) if 'vibrato_rate_known' in d.files else arr('vibrato_known',0),
                arr('vibrato_onset_known',0) if 'vibrato_onset_known' in d.files else arr('vibrato_known',0),
                arr('vibrato_jitter_known',0) if 'vibrato_jitter_known' in d.files else arr('vibrato_known',0))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--index',required=True);ap.add_argument('--out',default='checkpoints/vibrato_expert.pt')
    ap.add_argument('--epochs',type=int,default=80);ap.add_argument('--batch',type=int,default=16);ap.add_argument('--lr',type=float,default=2e-4)
    ap.add_argument('--registry',default='training/dataset_registry.json');ap.add_argument('--seed',type=int,default=1337);a=ap.parse_args()
    validate_index(a.index,a.registry); random.seed(a.seed);np.random.seed(a.seed);torch.manual_seed(a.seed)
    dev='cuda' if torch.cuda.is_available() else 'cpu';ds=VibDataset(a.index)
    if not ds: raise RuntimeError('No vibrato segments.')
    known_total=0.0
    for r in ds.rows:
        d=np.load(r['file'])
        if 'vibrato_depth_known' in d.files: known_total += float(np.asarray(d['vibrato_depth_known']).sum())
        elif 'vibrato_known' in d.files: known_total += float(np.asarray(d['vibrato_known']).sum())
    if known_total < 1.0:
        print('[NO_VIBRATO_SUPERVISION] No rights-cleared vibrato_known frames yet. Record/import/analyze CC3 material first.')
        sys.exit(3)
    # Prefer rights-cleared custom sessions, then professional Good-sounds/Ghent sources.
    weights=[]
    for r in ds.rows:
        src=str(r.get('dataset','')).lower();weights.append({'custom_owned_session':10.0,'good_sounds_cora_2025':4.0,'ghent_ar_violin_2023':2.0}.get(src,1.0))
    dl=DataLoader(ds,batch_size=a.batch,sampler=WeightedRandomSampler(weights,max(len(ds),64),replacement=True))
    m=VibratoControlExpert().to(dev);opt=torch.optim.AdamW(m.parameters(),a.lr,weight_decay=.01);best=1e9
    for ep in range(a.epochs):
        m.train();tot=0.;steps=0;known_frames=0.
        for batch in dl:
            cc3,dyn,pitch,nprog,phr,bpm,durb,speed_prof,ins,depth,rate,onset,jitter,kd,kr,ko,kj=[x.to(dev) for x in batch]
            pred=m(cc3,dyn,pitch,nprog,phr,bpm,durb,speed_prof,ins)
            target=torch.stack([depth,rate,onset,jitter],-1); mask=torch.stack([kd,kr,ko,kj],-1).clamp(0,1)
            denom=mask.sum().clamp_min(1.0); loss=((pred-target).pow(2)*mask).sum()/denom
            # Depth is the user-facing CC3 axis, so weight it more strongly. Straight/no-vibrato
            # material may supervise depth without falsely supervising rate/onset/jitter.
            depth_loss=(((pred[...,0]-target[...,0]).pow(2))*kd).sum()/kd.sum().clamp_min(1.0)
            loss=loss+.65*depth_loss
            opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.0);opt.step()
            tot+=float(loss.detach());steps+=1;known_frames+=float(mask.sum())
        score=tot/max(1,steps);print(f'epoch {ep+1:03d} vib_loss={score:.6f} known_frames={known_frames:.0f}')
        ck={'model':m.state_dict(),'epoch':ep+1,'schema_version':8,'outputs':['depth_cents/100','rate_hz/10','onset_ms/1000','jitter']}
        Path(a.out).parent.mkdir(parents=True,exist_ok=True);torch.save(ck,a.out)
        if score<best: best=score;torch.save(ck,str(Path(a.out).with_name(Path(a.out).stem+'_best.pt')))
if __name__=='__main__':main()
