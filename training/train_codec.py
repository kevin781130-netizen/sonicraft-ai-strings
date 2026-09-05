from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler
from audio_dataset import AudioManifestDataset, audio_manifest_collate
from models.string_codec import StringCodec
from models.string_vae64 import StringVAE64
from models.string_physics_probe import StringPhysicsProbe, physics_targets, masked_physics_loss
from models.stft_discriminator import MultiResolutionSTFTDiscriminator, discriminator_hinge, generator_adversarial, feature_matching
from losses import mrstft_loss, codec_mrstft_loss
from physics_latent_alignment import physics_metric_alignment_loss
from string_source_mixer import load_registry, build_curriculum_weights, mixture_audit, coverage_audit, modeled_mask


def set_grad(module, flag):
    for p in module.parameters():
        p.requires_grad_(flag)


def recon_loss(fake, real):
    return codec_mrstft_loss(fake.float(), real.float()) + .05 * (fake-real).abs().mean()

from promotion_binding import promotion_binding

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',action='append',required=True)
    ap.add_argument('--out',default='checkpoints/strings_vae64.pt')
    ap.add_argument('--decoder-out',default=None)
    ap.add_argument('--arch',choices=('vae64','legacy'),default='vae64')
    ap.add_argument('--width',type=int,default=24,help='VAE64 base width. 16=micro, 24=balanced frontier.')
    ap.add_argument('--epochs',type=int,default=80); ap.add_argument('--batch',type=int,default=4)
    ap.add_argument('--lr',type=float,default=1.5e-4); ap.add_argument('--disc-lr',type=float,default=3e-4)
    ap.add_argument('--adv-start',type=int,default=5); ap.add_argument('--adv-weight',type=float,default=.10)
    ap.add_argument('--fm-weight',type=float,default=5.0); ap.add_argument('--kl-weight',type=float,default=1e-5)
    # v1.8 REAL80 / MODEL20 lane. Modeled audio teaches physics, not final timbre.
    ap.add_argument('--registry',default='training/dataset_registry.json')
    ap.add_argument('--real-ratio',type=float,default=.80); ap.add_argument('--modeled-ratio',type=float,default=.20)
    ap.add_argument('--modeled-recon-weight',type=float,default=.20,
                    help='Additional reconstruction down-weight for modeled audio; real recordings remain the timbre anchor.')
    ap.add_argument('--physics-weight',type=float,default=.15,help='Training-only latent physics-probe loss weight.')
    ap.add_argument('--physics-metric-weight',type=float,default=.03,help='v1.9 parameter-free modeled-lane latent/physics geometry alignment.')
    ap.add_argument('--require-modeled',action='store_true',help='Fail if the 20%% clean-room lane is missing.')
    ap.add_argument('--acoustic-promotion',help='Passed v2.0 acoustic promotion report; binds codec checkpoint to winner evidence.')
    a=ap.parse_args(); promotion_id,curriculum=promotion_binding(a.acoustic_promotion)

    dev='cuda' if torch.cuda.is_available() else 'cpu'
    ds=AudioManifestDataset(a.manifest)
    registry=load_registry(a.registry)
    weights=build_curriculum_weights(ds.rows,registry,a.real_ratio,a.modeled_ratio,progress=0.0,require_modeled=a.require_modeled)
    audit=mixture_audit(ds.rows,weights,registry)
    print('string mixture',json.dumps(audit,sort_keys=True))
    print('coverage curriculum',json.dumps(coverage_audit(ds.rows,weights,registry),sort_keys=True))
    sampler=WeightedRandomSampler(weights,max(len(ds),128),replacement=True)
    dl=DataLoader(ds,a.batch,sampler=sampler,num_workers=0,collate_fn=audio_manifest_collate,
                  pin_memory=torch.cuda.is_available())
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)

    if a.arch=='legacy':
        m=StringCodec().to(dev); opt=torch.optim.AdamW(m.parameters(),2e-4,betas=(.8,.99))
        print('legacy codec params',sum(p.numel() for p in m.parameters()),'device',dev,'clips',len(ds))
        for ep in range(a.epochs):
            m.train(); tot=0.
            for wav,_rows in dl:
                wav=wav.to(dev); rec=m(wav); n=min(wav.shape[-1],rec.shape[-1]); wav=wav[...,:n]; rec=rec[...,:n]
                loss=(wav-rec).abs().mean()+0.7*mrstft_loss(rec,wav)
                opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(m.parameters(),5.); opt.step(); tot+=loss.item()
            print(f'epoch {ep+1:03d} loss={tot/max(1,len(dl)):.5f}')
            torch.save({'model':m.state_dict(),'latent':96,'epoch':ep+1,'codec_kind':'legacy_stringcodec','latent_hz':187.5,'codec_sample_rate':48000,
                        'training_mix':{'real':a.real_ratio,'modeled':a.modeled_ratio,'curriculum':curriculum},'acoustic_promotion_id':promotion_id},a.out)
        return

    m=StringVAE64(channels=a.width).to(dev)
    # Probe is deliberately training-only and excluded from decoder-only checkpoints.
    probe=StringPhysicsProbe(latent_dim=m.latent_dim).to(dev)
    disc=MultiResolutionSTFTDiscriminator().to(dev)
    opt=torch.optim.AdamW(list(m.parameters())+list(probe.parameters()),a.lr,betas=(.8,.99),weight_decay=1e-3)
    dopt=torch.optim.AdamW(disc.parameters(),a.disc_lr,betas=(.8,.99),weight_decay=1e-3)
    total=sum(p.numel() for p in m.parameters()); dec=sum(p.numel() for p in m.decoder.parameters()); pp=sum(p.numel() for p in probe.parameters())
    print('VAE64 params',total,'decoder_only',dec,'training_probe',pp,'device',dev,'clips',len(ds),'width',a.width,
          'latent',m.latent_dim,'downsample',m.downsampling_ratio,'latent_hz',m.latent_hz)
    use_amp=(dev=='cuda' and torch.cuda.is_bf16_supported())
    ampctx=lambda: torch.autocast(device_type='cuda',dtype=torch.bfloat16,enabled=use_amp)
    decoder_out=Path(a.decoder_out) if a.decoder_out else Path(a.out).with_name('strings_vae64_decoder.pt')

    for ep in range(a.epochs):
        progress=ep/max(1,a.epochs-1)
        sampler.weights=torch.as_tensor(build_curriculum_weights(ds.rows,registry,a.real_ratio,a.modeled_ratio,progress=progress,require_modeled=a.require_modeled),dtype=torch.double)
        m.train(); probe.train(); disc.train()
        sums={'g':0.,'recon':0.,'real_recon':0.,'modeled_recon':0.,'physics':0.,'physics_metric':0.,'kl':0.,'adv':0.,'fm':0.,'d':0.}; steps=0
        adv_on=ep>=a.adv_start
        for wav,rows in dl:
            wav=wav.to(dev,non_blocking=True); mm=modeled_mask(rows,registry,device=dev); rm=~mm
            with ampctx():
                rec,mu,logvar=m(wav,sample=True); n=min(wav.shape[-1],rec.shape[-1]); real=wav[...,:n]; fake=rec[...,:n]

            # The discriminator only sees REAL recordings. Synthetic/model audio can never become the realism target.
            has_real=bool(rm.any().item())
            if adv_on and has_real:
                set_grad(disc,True); dopt.zero_grad(set_to_none=True)
                with ampctx():
                    ro=disc(real[rm]); fo=disc(fake[rm].detach()); dloss=discriminator_hinge(ro,fo)
                dloss.backward(); torch.nn.utils.clip_grad_norm_(disc.parameters(),10.); dopt.step()
            else:
                dloss=fake.new_tensor(0.)

            set_grad(disc,False); opt.zero_grad(set_to_none=True)
            with ampctx():
                real_recon=recon_loss(fake[rm],real[rm]) if has_real else fake.new_tensor(0.)
                has_modeled=bool(mm.any().item())
                modeled_recon=recon_loss(fake[mm],real[mm]) if has_modeled else fake.new_tensor(0.)
                # Sampling is already 80/20. A second modeled reconstruction down-weight keeps synthetic timbre from defining the decoder.
                recon=real_recon + a.modeled_recon_weight*modeled_recon
                lv=logvar.clamp(-20,10); kl=-.5*(1+lv-mu.square()-lv.exp()).mean()
                ptarget,pmask=physics_targets(rows,device=dev)
                ppred=probe(mu)
                physics=masked_physics_loss(ppred.float(),ptarget,pmask)
                physics_metric=physics_metric_alignment_loss(mu.float(),ptarget,pmask,mm)
                if adv_on and has_real:
                    with torch.no_grad(): ro=disc(real[rm])
                    fo=disc(fake[rm]); adv=generator_adversarial(fo); fm=feature_matching(ro,fo)
                else:
                    adv=fake.new_tensor(0.); fm=fake.new_tensor(0.)
                gloss=recon + a.physics_weight*physics + a.physics_metric_weight*physics_metric + a.kl_weight*kl + a.adv_weight*adv + a.fm_weight*fm
            gloss.backward(); torch.nn.utils.clip_grad_norm_(list(m.parameters())+list(probe.parameters()),1000.); opt.step(); set_grad(disc,True)
            for k,v in [('g',gloss),('recon',recon),('real_recon',real_recon),('modeled_recon',modeled_recon),('physics',physics),('physics_metric',physics_metric),('kl',kl),('adv',adv),('fm',fm),('d',dloss)]:
                sums[k]+=float(v.detach())
            steps+=1
        q={k:v/max(1,steps) for k,v in sums.items()}; print(f"epoch {ep+1:03d} "+' '.join(f'{k}={v:.5f}' for k,v in q.items()))
        cfg=m.config(); common={'epoch':ep+1,'codec_kind':'strings_vae64','codec_sample_rate':m.sample_rate,
             'latent_ch':m.latent_dim,'latent_hz':m.latent_hz,'downsampling_ratio':m.downsampling_ratio,'config':cfg,
             'training_mix':{'real':a.real_ratio,'modeled':a.modeled_ratio,'modeled_recon_weight':a.modeled_recon_weight,'curriculum':curriculum},
             'acoustic_promotion_id':promotion_id,
             'physics_probe_training_only':True,'physics_metric_weight':a.physics_metric_weight,'sound_forge':'sound_forge_v19'}
        torch.save({**common,'model':m.state_dict(),'physics_probe':probe.state_dict(),'optimizer':opt.state_dict(),'discriminator':disc.state_dict()},a.out)
        decoder_out.parent.mkdir(parents=True,exist_ok=True)
        # Deliberately no probe/discriminator/encoder optimizer in consumer artifact.
        torch.save({**common,'decoder':m.decoder.state_dict(),'decoder_params':dec},decoder_out)

if __name__=='__main__': main()
