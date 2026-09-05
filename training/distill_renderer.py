from __future__ import annotations
import argparse, copy, json
from pathlib import Path
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler
from models.ballad_flow_renderer import BalladFlowRenderer
from train_ballad_renderer import Segments, collate, source_weights, PRESETS, ema_update
from promotion_binding import promotion_binding
from source_policy import validate_index
from string_source_mixer import load_registry, build_curriculum_weights, mixture_audit

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--index',default='datasets/processed/ballad_dac/index.jsonl')
    ap.add_argument('--teacher',required=True); ap.add_argument('--out',default='checkpoints/compact_distilled.pt')
    ap.add_argument('--epochs',type=int,default=60); ap.add_argument('--batch',type=int,default=2); ap.add_argument('--accum',type=int,default=1)
    ap.add_argument('--registry',default='training/dataset_registry.json'); ap.add_argument('--alpha',type=float,default=.55)
    ap.add_argument('--real-ratio',type=float,default=.80); ap.add_argument('--modeled-ratio',type=float,default=.20)
    ap.add_argument('--modeled-flow-weight',type=float,default=.35,help='Modeled clips teach transition physics but are down-weighted as endpoint/timbre distillation targets.')
    ap.add_argument('--student-preset',choices=PRESETS,default='compact'); ap.add_argument('--acoustic-promotion'); a=ap.parse_args(); promotion_id,curriculum=promotion_binding(a.acoustic_promotion)
    validate_index(a.index,a.registry); dev='cuda' if torch.cuda.is_available() else 'cpu'; ds=Segments(a.index)
    registry=load_registry(a.registry); weights=build_curriculum_weights(ds.rows,registry,a.real_ratio,a.modeled_ratio,progress=0.0)
    print('distill string mixture',json.dumps(mixture_audit(ds.rows,weights,registry),sort_keys=True))
    modeled_sources={str(k).lower() for k,v in registry.items() if str(v.get('training_origin','real')).lower()=='modeled'}
    sampler=WeightedRandomSampler(weights,max(len(ds),128),replacement=True)
    dl=DataLoader(ds,batch_size=a.batch,sampler=sampler,collate_fn=collate)
    tck=torch.load(a.teacher,map_location='cpu'); tcfg=tck['config']; latent_ch=int(tck.get('latent_ch',1024))
    teacher=BalladFlowRenderer(latent_ch=latent_ch,**tcfg).to(dev).eval(); teacher.load_state_dict(tck.get('ema',tck['model']))
    student=BalladFlowRenderer(latent_ch=latent_ch,**PRESETS[a.student_preset]).to(dev); ema=copy.deepcopy(student).eval().requires_grad_(False)
    opt=torch.optim.AdamW(student.parameters(),1.0e-4,weight_decay=.01,betas=(.9,.95))
    for ep in range(a.epochs):
        progress=ep/max(1,a.epochs-1); sampler.weights=torch.as_tensor(build_curriculum_weights(ds.rows,registry,a.real_ratio,a.modeled_ratio,progress=progress),dtype=torch.double)
        student.train(); total=cont_total=0.; n=0; opt.zero_grad(set_to_none=True)
        for bi,batch in enumerate(dl):
            *vals,dsnames=batch; vals=[x.to(dev) for x in vals]
            (z,p,g,o,vel,d,vib,exp,leg,pb,ts,st,ac,np_,phr,pi,ni,bow,vib_on,
             bpm,spb,dur_b,trans_ms,speed_prof,vib_depth,vib_rate,vib_jit,
             dk,vk,vpk,ek,lk,pk,tk,ak,ins,art,player,art_curve)=vals
            noise=torch.randn_like(z); time=torch.rand(z.shape[0],device=dev); tt=time[:,None,None]; xt=(1-tt)*noise+tt*z; target=z-noise
            args=(xt,time,p,g,o,vel,d,vib,exp,leg,pb,ts,st,ac,np_,phr,pi,ni,bow,vib_on,
                  bpm,spb,dur_b,trans_ms,speed_prof,vib_depth,vib_rate,vib_jit,
                  dk,vk,ek,lk,pk,tk,ak,ins,art,player,art_curve)
            with torch.no_grad(): tp=teacher(*args,vibrato_physics_known=vpk)
            sp=student(*args,vibrato_physics_known=vpk)
            hard_per=(sp-target).pow(2).mean(dim=(1,2)); soft_per=(sp-tp).pow(2).mean(dim=(1,2))
            sw=torch.tensor([a.modeled_flow_weight if str(x).lower() in modeled_sources else 1.0 for x in dsnames],device=dev,dtype=hard_per.dtype)
            hard=(hard_per*sw).sum()/sw.sum().clamp_min(1e-6); soft=(soft_per*sw).sum()/sw.sum().clamp_min(1e-6)
            # Modeled clips keep full authority over local transition shape while their endpoint/timbre pressure is reduced.
            continuity=((sp[...,1:]-sp[...,:-1])-(tp[...,1:]-tp[...,:-1])).abs().mean() if sp.shape[-1]>1 else hard.new_tensor(0.)
            loss=(1-a.alpha)*hard+a.alpha*soft+.05*continuity
            (loss/a.accum).backward()
            if (bi+1)%a.accum==0:
                torch.nn.utils.clip_grad_norm_(student.parameters(),1.0); opt.step(); opt.zero_grad(set_to_none=True); ema_update(ema,student,.999)
            total+=float(loss.detach()); cont_total+=float(continuity.detach()); n+=1
        print(f'epoch {ep+1:03d} distill={total/max(1,n):.6f} transition={cont_total/max(1,n):.6f}')
        Path(a.out).parent.mkdir(parents=True,exist_ok=True); torch.save({'model':student.state_dict(),'ema':ema.state_dict(),'epoch':ep+1,'config':PRESETS[a.student_preset],'teacher':a.teacher,'distill_alpha':a.alpha,'schema_version':10,'latent_ch':latent_ch,'latent_hz':float(tck.get('latent_hz',25.0)),'codec_kind':tck.get('codec_kind','dac44'),'codec_sample_rate':int(tck.get('codec_sample_rate',44100)),
                    'training_mix':{'real':a.real_ratio,'modeled':a.modeled_ratio,'modeled_flow_weight':a.modeled_flow_weight,'curriculum':curriculum},'acoustic_promotion_id':promotion_id},a.out)
if __name__=='__main__': main()
