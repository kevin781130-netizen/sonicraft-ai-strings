from __future__ import annotations
import argparse,json,random
from pathlib import Path
import torch
from torch.utils.data import DataLoader
from audio_dataset import AudioManifestDataset
from models.realism_critic import RealismCritic
from source_policy import assert_commercial_sources

def read_ids(paths):
    ids=[]
    for p in paths:
        for line in Path(p).read_text(encoding='utf-8').splitlines():
            if line.strip(): ids.append(json.loads(line).get('dataset','unknown'))
    return ids

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--real-manifest',action='append',required=True);ap.add_argument('--generated-manifest',action='append',required=True);ap.add_argument('--registry',default='training/dataset_registry.json');ap.add_argument('--out',default='checkpoints/realism_critic.pt');ap.add_argument('--epochs',type=int,default=20);ap.add_argument('--batch',type=int,default=4);a=ap.parse_args()
    assert_commercial_sources(read_ids(a.real_manifest),a.registry)
    real=AudioManifestDataset(a.real_manifest,sample_rate=48000,seconds=4.0); fake=AudioManifestDataset(a.generated_manifest,sample_rate=48000,seconds=4.0)
    rd=DataLoader(real,batch_size=a.batch,shuffle=True,drop_last=True); fd=DataLoader(fake,batch_size=a.batch,shuffle=True,drop_last=True)
    dev='cuda' if torch.cuda.is_available() else 'cpu'; m=RealismCritic().to(dev); opt=torch.optim.AdamW(m.parameters(),2e-4,betas=(.5,.9)); bce=torch.nn.BCEWithLogitsLoss()
    for ep in range(a.epochs):
        tot=0.; n=0
        for (rw,_),(fw,_) in zip(rd,fd):
            rw,fw=rw.to(dev),fw.to(dev); lr=m(rw); lf=m(fw); loss=bce(lr,torch.ones_like(lr))+bce(lf,torch.zeros_like(lf))
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step(); tot+=float(loss);n+=1
        print(f'epoch {ep+1:03d} critic={tot/max(1,n):.5f}')
        Path(a.out).parent.mkdir(parents=True,exist_ok=True);torch.save({'model':m.state_dict(),'epoch':ep+1},a.out)
if __name__=='__main__': main()
