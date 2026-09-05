from __future__ import annotations
import argparse,json,random
from pathlib import Path
import numpy as np, torch
from torch.utils.data import Dataset,DataLoader
from models.flow_renderer import FlowRenderer

class Segments(Dataset):
    def __init__(self,index):self.rows=[json.loads(x) for x in Path(index).read_text().splitlines() if x.strip()]
    def __len__(self):return len(self.rows)
    def __getitem__(self,i):
        d=np.load(self.rows[i]['file']);
        if 'latent' not in d: raise RuntimeError('Run encode_latents.py first')
        return (torch.from_numpy(d['latent'].astype('float32')),torch.from_numpy(d['pitch']),torch.from_numpy(d['gate']),torch.from_numpy(d['dynamics']),torch.tensor(int(d['instrument'])))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--index',default='datasets/processed/urmp48/index.jsonl'); ap.add_argument('--out',default='checkpoints/renderer_s.pt'); ap.add_argument('--epochs',type=int,default=120); ap.add_argument('--batch',type=int,default=4); a=ap.parse_args()
    dev='cuda' if torch.cuda.is_available() else 'cpu'; ds=Segments(a.index); dl=DataLoader(ds,a.batch,shuffle=True,num_workers=0); m=FlowRenderer().to(dev); opt=torch.optim.AdamW(m.parameters(),2e-4,weight_decay=.01)
    print('params',sum(p.numel() for p in m.parameters()),'device',dev,'segments',len(ds))
    for ep in range(a.epochs):
        m.train(); tot=0
        for z,p,g,d,ins in dl:
            z,p,g,d,ins=[x.to(dev) for x in (z,p,g,d,ins)]; noise=torch.randn_like(z); t=torch.rand(z.shape[0],device=dev); tt=t[:,None,None]
            xt=(1-tt)*noise+tt*z; target=z-noise; pred=m(xt,t,p,g,d,ins); loss=(pred-target).pow(2).mean()
            opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(),1.0); opt.step(); tot+=loss.item()
        print(f'epoch {ep+1:03d} flow={tot/max(1,len(dl)):.6f}')
        Path(a.out).parent.mkdir(parents=True,exist_ok=True); torch.save({'model':m.state_dict(),'epoch':ep+1},a.out)
if __name__=='__main__':main()
