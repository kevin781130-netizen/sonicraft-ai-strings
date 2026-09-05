from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler
from audio_dataset import AudioManifestDataset
from losses import mrstft_loss

def load_dac(bitrate='16kbps'):
    import dac
    try: path=dac.utils.download(model_type='44khz',model_bitrate=bitrate)
    except TypeError: path=dac.utils.download(model_type='44khz')
    return dac.DAC.load(path)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',action='append',required=True); ap.add_argument('--out',default='checkpoints/dac_strings_decoder.pt')
    ap.add_argument('--epochs',type=int,default=30); ap.add_argument('--batch',type=int,default=3); ap.add_argument('--seconds',type=float,default=2.0); ap.add_argument('--bitrate',default='16kbps'); a=ap.parse_args()
    dev='cuda' if torch.cuda.is_available() else 'cpu'
    ds=AudioManifestDataset(a.manifest,sample_rate=44100,seconds=a.seconds,peak_normalize=False)
    # Iowa is the high-resolution fidelity anchor; do not let smaller/older sources dominate it.
    source_weight={'iowa_mis':4.0,'good_sounds_cora_2025':3.0,'ghent_ar_violin_2023':1.5,'sanidha':1.25,'tinysol':1.0}
    weights=[source_weight.get(str(r.get('dataset') or r.get('dataset_id') or '').lower(),1.0) for r in ds.rows]
    sampler=WeightedRandomSampler(weights,num_samples=max(len(ds),64),replacement=True)
    dl=DataLoader(ds,batch_size=a.batch,sampler=sampler,num_workers=0,pin_memory=torch.cuda.is_available())
    m=load_dac(a.bitrate).to(dev); m.train()
    for p in m.encoder.parameters(): p.requires_grad=False
    for p in m.quantizer.parameters(): p.requires_grad=False
    opt=torch.optim.AdamW(m.decoder.parameters(),lr=1e-5,betas=(.8,.99),weight_decay=1e-4)
    print('device',dev,'clips',len(ds),'decoder params',sum(p.numel() for p in m.decoder.parameters()))
    for ep in range(a.epochs):
        tot=0.; nstep=0
        for wav,_ in dl:
            wav=wav.to(dev,non_blocking=True)
            with torch.no_grad():
                x=m.preprocess(wav,44100); z,_,_,_,_=m.encode(x)
            rec=m.decode(z)[...,:wav.shape[-1]]
            loss=(rec-wav).abs().mean()+0.65*mrstft_loss(rec,wav)
            opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(m.decoder.parameters(),5.); opt.step(); tot+=float(loss); nstep+=1
        print(f'epoch {ep+1:03d} decoder_loss={tot/max(1,nstep):.6f}')
        Path(a.out).parent.mkdir(parents=True,exist_ok=True)
        torch.save({'decoder':m.decoder.state_dict(),'epoch':ep+1,'sample_rate':44100,'base':'descript-dac-44khz','bitrate':a.bitrate,
                    'provenance_manifests':a.manifest},a.out)
if __name__=='__main__': main()
