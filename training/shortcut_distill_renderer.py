from __future__ import annotations
"""Dyadic shortcut training for the SONICRAFT flow renderer.

MIT acceleration reference: kvfrans/shortcut-models. The key idea is preserved while
adapting it to continuous string latents and strict MIDI-authority conditioning:
- the same renderer is conditioned on desired jump size ``flow_h``;
- smallest jumps receive ordinary flow-matching supervision from real latent pairs;
- larger dyadic jumps bootstrap from two EMA half-jumps;
- only one student network ships at runtime and it can serve 1/2/4/8-step budgets.

This is training-only. It adds no teacher or auxiliary model to the consumer package.
"""
import argparse, copy, math, random, json, os
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler

from models.ballad_flow_renderer import BalladFlowRenderer
from train_ballad_renderer import Segments, collate, source_weights, PRESETS, ema_update, infer_latent_geometry
from promotion_binding import promotion_binding
from source_policy import validate_index
from string_source_mixer import load_registry, build_curriculum_weights, mixture_audit


def atomic_torch_save(obj, path):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp')
    torch.save(obj,tmp)
    os.replace(tmp,p)

CONTROL_NAMES=(
    'pitch','gate','onset','velocity','dynamics','vibrato','expression','legato','pitchbend',
    'transition_speed','short_tightness','attack_character','note_progress','phrase_position',
    'prev_interval','next_interval','bow_change_prob','vibrato_onset','tempo_bpm','seconds_per_beat',
    'note_duration_beats','transition_target_ms','speed_profile','vibrato_depth_cents','vibrato_rate_hz',
    'vibrato_jitter','dynamics_known','vibrato_known','vibrato_physics_known','expression_known','legato_known','pitchbend_known',
    'timing_known','articulation_known','instrument','articulation','player','articulation_curve'
)

_EXPRESSIVE_ZERO={
    'dynamics','vibrato','expression','legato','pitchbend','transition_speed','short_tightness',
    'attack_character','bow_change_prob','vibrato_onset','tempo_bpm','seconds_per_beat',
    'note_duration_beats','transition_target_ms','speed_profile','vibrato_depth_cents',
    'vibrato_rate_hz','vibrato_jitter','dynamics_known','vibrato_known','vibrato_physics_known','expression_known',
    'legato_known','pitchbend_known','timing_known'
}


def split_batch(batch,dev):
    *vals,dsnames=batch
    vals=[x.to(dev,non_blocking=True) for x in vals]
    z=vals[0]; controls=dict(zip(CONTROL_NAMES,vals[1:]))
    return z,controls,dsnames


def dropout_controls(controls,p):
    if p<=0: return controls
    # One dropout decision per phrase/part. Score authority and articulation stay intact.
    any_tensor=next(v for v in controls.values() if torch.is_tensor(v))
    b=int(any_tensor.shape[0])
    keep=(torch.rand(b,device=any_tensor.device)>=float(p)).float()
    out={}
    for k,v in controls.items():
        if k in _EXPRESSIVE_ZERO and torch.is_tensor(v):
            shape=(b,)+(1,)*(v.ndim-1)
            out[k]=v*keep.view(shape)
        else:
            out[k]=v
    return out


def dyadic_jump(batch, max_steps, device):
    """Return t,h where h in {1,1/2,...,2/max_steps} and t+h <= 1."""
    max_steps=int(max_steps)
    if max_steps<2 or (max_steps & (max_steps-1)):
        raise ValueError('max_steps must be a power of two >= 2')
    levels=int(math.log2(max_steps))
    level=torch.randint(0,levels,(batch,),device=device)
    h=torch.pow(torch.tensor(2.0,device=device),-level.float())
    sections=torch.round(1.0/h).long().clamp_min(1)
    # Sampling via uniform then floor avoids per-row randint bounds.
    k=torch.floor(torch.rand(batch,device=device)*sections.float()).long()
    t=k.float()/sections.float()
    return t,h


def string_importance(controls, T):
    """Parameter-free perceptual importance for string transitions.

    One-step errors around attacks, legato joins, bow changes and authored vibrato bloom
    are much more audible than equal latent MSE in steady sustain.  This is training-only
    weighting: it adds zero runtime parameters and keeps score authority untouched.
    """
    def interp(name,default=0.0):
        v=controls.get(name)
        if v is None:
            ref=next(x for x in controls.values() if torch.is_tensor(x)); return ref.new_full((ref.shape[0],T),float(default))
        if v.ndim==1: v=v[:,None]
        return torch.nn.functional.interpolate(v[:,None].float(),size=T,mode='linear',align_corners=False)[:,0]
    on=interp('onset').clamp(0,1); leg=interp('legato').clamp(0,1); bow=interp('bow_change_prob').clamp(0,1)
    vib=interp('vibrato').clamp(0,1); von=interp('vibrato_onset').clamp(0,1)
    return (1.0+2.0*on+0.65*leg+0.85*bow+0.45*vib+0.55*von)[:,None,:]


def shortcut_losses(model, ema, z, controls, max_steps=8, cond_dropout=.08, sample_weight=None):
    b=z.shape[0]; dev=z.device
    c=dropout_controls(controls,cond_dropout)
    h_min=1.0/float(max_steps)

    # 1) Ground-truth flow anchor at the smallest supported jump.
    n0=torch.randn_like(z); t=torch.rand(b,device=dev)*(1.0-h_min); tt=t[:,None,None]
    xt=(1-tt)*n0+tt*z; target=z-n0
    h=torch.full((b,),h_min,device=dev,dtype=z.dtype)
    pred=model(xt,t,flow_h=h,**c)
    importance=string_importance(c,z.shape[-1]).to(dtype=pred.dtype)
    flow_per=((pred-target).pow(2)*importance).mean(dim=(1,2))
    sw=torch.ones_like(flow_per) if sample_weight is None else sample_weight.to(device=dev,dtype=flow_per.dtype)
    flow=(flow_per*sw).sum()/sw.sum().clamp_min(1e-6)

    # 2) Larger shortcut target = mean of two EMA half-jump velocities.
    tb,hb=dyadic_jump(b,max_steps,dev); ttb=tb[:,None,None]
    nb=torch.randn_like(z); xb=(1-ttb)*nb+ttb*z; half=hb*.5
    with torch.no_grad():
        v1=ema(xb,tb,flow_h=half,**c)
        xm=xb+half[:,None,None]*v1
        v2=ema(xm,tb+half,flow_h=half,**c)
        v_target=(v1+v2)*.5
    v=model(xb,tb,flow_h=hb,**c)
    boot_per=((v-v_target).pow(2)*importance).mean(dim=(1,2))
    boot=(boot_per*sw).sum()/sw.sum().clamp_min(1e-6)
    # Endpoint consistency protects large/one-step jumps: the audible result depends on
    # where the shortcut lands, not only on matching its local velocity field.
    endpoint=((xb+hb[:,None,None]*v)-(xb+hb[:,None,None]*v_target)).abs()
    endpoint_per=(endpoint*importance).mean(dim=(1,2))
    endpoint=(endpoint_per*sw).sum()/sw.sum().clamp_min(1e-6)

    # Preserve local string texture/transition smoothness in the learned jump field.
    if z.shape[-1]>1:
        dv=v[...,1:]-v[...,:-1]; dt=v_target[...,1:]-v_target[...,:-1]
        continuity=(dv-dt).abs().mean()
    else: continuity=boot.new_tensor(0.)
    loss=flow+boot+0.12*endpoint+0.05*continuity
    return loss,{'flow':flow.detach(),'bootstrap':boot.detach(),'endpoint':endpoint.detach(),'continuity':continuity.detach(),
                 'mean_h':hb.mean().detach(),'modeled_fraction':(sw<1).float().mean().detach()}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--index',default='datasets/processed/ballad_vae64/index.jsonl')
    ap.add_argument('--init',help='Optional matching v1.7 flow checkpoint to initialize student/EMA.')
    ap.add_argument('--resume',help='Resume shortcut training from its own checkpoint; takes precedence over --init.')
    ap.add_argument('--out',default='checkpoints/frontier_shortcut.pt')
    ap.add_argument('--preset',choices=PRESETS,default='frontier_shared_dit')
    ap.add_argument('--max-steps',type=int,default=8,help='Power-of-two training grid. Produces 1/2/4/... step inference.')
    ap.add_argument('--recommend-steps',type=int,default=2)
    ap.add_argument('--epochs',type=int,default=40); ap.add_argument('--batch',type=int,default=1); ap.add_argument('--accum',type=int,default=1)
    ap.add_argument('--lr',type=float,default=8e-5); ap.add_argument('--ema',type=float,default=.9995)
    ap.add_argument('--cond-dropout',type=float,default=.08); ap.add_argument('--registry',default='training/dataset_registry.json')
    ap.add_argument('--real-ratio',type=float,default=.80); ap.add_argument('--modeled-ratio',type=float,default=.20)
    ap.add_argument('--modeled-flow-weight',type=float,default=.35)
    ap.add_argument('--seed',type=int,default=1701)
    ap.add_argument('--acoustic-promotion')
    a=ap.parse_args(); promotion_id,curriculum=promotion_binding(a.acoustic_promotion); random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    if a.max_steps<2 or (a.max_steps & (a.max_steps-1)): raise SystemExit('--max-steps must be a power of two >= 2')
    if a.recommend_steps<1 or a.max_steps%a.recommend_steps: raise SystemExit('--recommend-steps must divide max-steps')
    validate_index(a.index,a.registry); dev='cuda' if torch.cuda.is_available() else 'cpu'
    ds=Segments(a.index); latent_ch,latent_hz,codec_kind,codec_sr=infer_latent_geometry(ds)
    registry=load_registry(a.registry); weights=build_curriculum_weights(ds.rows,registry,a.real_ratio,a.modeled_ratio,progress=0.0)
    print('shortcut string mixture',json.dumps(mixture_audit(ds.rows,weights,registry),sort_keys=True))
    modeled_sources={str(k).lower() for k,v in registry.items() if str(v.get('training_origin','real')).lower()=='modeled'}
    sampler=WeightedRandomSampler(weights,max(len(ds),128),replacement=True)
    dl=DataLoader(ds,batch_size=a.batch,sampler=sampler,collate_fn=collate,num_workers=0,pin_memory=torch.cuda.is_available())

    cfg=dict(PRESETS[a.preset])
    if not cfg.get('interval_conditioning'):
        raise SystemExit('shortcut training requires a preset with interval_conditioning=True')
    m=BalladFlowRenderer(latent_ch=latent_ch,**cfg).to(dev)
    ema=copy.deepcopy(m).eval().requires_grad_(False)
    resume_ck=None
    if a.resume:
        resume_ck=torch.load(a.resume,map_location='cpu')
        if dict(resume_ck.get('config') or {})!=cfg: raise RuntimeError('resume shortcut architecture mismatch')
        if data_fingerprint and resume_ck.get('data_fingerprint')!=data_fingerprint: raise RuntimeError(f'resume shortcut data fingerprint mismatch: saved={resume_ck.get("data_fingerprint")} current={data_fingerprint}')
        if recipe_fingerprint and resume_ck.get('recipe_fingerprint')!=recipe_fingerprint: raise RuntimeError(f'resume shortcut recipe fingerprint mismatch: saved={resume_ck.get("recipe_fingerprint")} current={recipe_fingerprint}')
        if int(resume_ck.get('latent_ch',latent_ch))!=latent_ch: raise RuntimeError('resume shortcut latent geometry mismatch')
        m.load_state_dict(resume_ck.get('model',resume_ck.get('ema')),strict=True)
        ema.load_state_dict(resume_ck.get('ema',resume_ck.get('model')),strict=True)
        print('loaded shortcut resume checkpoint',a.resume)
    elif a.init:
        ck=torch.load(a.init,map_location='cpu')
        if dict(ck.get('config') or {})!=cfg: raise RuntimeError('init checkpoint architecture does not match shortcut preset')
        if int(ck.get('latent_ch',latent_ch))!=latent_ch: raise RuntimeError('init latent geometry mismatch')
        m.load_state_dict(ck.get('model',ck.get('ema')),strict=True)
        ema.load_state_dict(ck.get('ema',ck.get('model')),strict=True)
        print('initialized shortcut model from',a.init)

    opt=torch.optim.AdamW(m.parameters(),lr=a.lr,weight_decay=.01,betas=(.9,.95))
    data_fingerprint=os.environ.get('SONICRAFT_DATA_FINGERPRINT') or None
    recipe_fingerprint=os.environ.get('SONICRAFT_RECIPE_FINGERPRINT') or None
    start=0
    if resume_ck is not None:
        if 'optimizer' in resume_ck: opt.load_state_dict(resume_ck['optimizer'])
        start=int(resume_ck.get('epoch',0))
        print('resumed shortcut at epoch',start,'target',a.epochs)
        if start>=a.epochs:
            print('shortcut target already complete; nothing to do')
            return
    use_amp=(dev=='cuda' and torch.cuda.is_bf16_supported())
    ampctx=lambda: torch.autocast(device_type='cuda',dtype=torch.bfloat16,enabled=use_amp)
    print('shortcut params',sum(p.numel() for p in m.parameters()),'preset',a.preset,'max_steps',a.max_steps,
          'latent',latent_ch,'@',latent_hz,'codec',codec_kind)
    for ep in range(start,a.epochs):
        progress=ep/max(1,a.epochs-1); sampler.weights=torch.as_tensor(build_curriculum_weights(ds.rows,registry,a.real_ratio,a.modeled_ratio,progress=progress),dtype=torch.double)
        m.train(); opt.zero_grad(set_to_none=True); sums={'flow':0.,'bootstrap':0.,'endpoint':0.,'continuity':0.,'mean_h':0.,'modeled_fraction':0.}; n=0; interrupted=False
        for bi,batch in enumerate(dl):
            z,c,dsnames=split_batch(batch,dev)
            sw=torch.tensor([a.modeled_flow_weight if str(x).lower() in modeled_sources else 1.0 for x in dsnames],device=dev,dtype=z.dtype)
            with ampctx(): loss,met=shortcut_losses(m,ema,z,c,a.max_steps,a.cond_dropout,sw); loss=loss/a.accum
            loss.backward()
            if (bi+1)%a.accum==0:
                torch.nn.utils.clip_grad_norm_(m.parameters(),1.0); opt.step(); opt.zero_grad(set_to_none=True); ema_update(ema,m,a.ema)
            for k,v in met.items(): sums[k]+=float(v)
            n+=1
            stop_file=os.environ.get('SONICRAFT_STOP_FILE')
            if stop_file and Path(stop_file).exists() and n < len(dl):
                interrupted=True
                print('[SAFE STOP] request seen after batch',n,'of',len(dl))
                break
        print(f"epoch {ep+1:03d} flow={sums['flow']/max(1,n):.6f} shortcut={sums['bootstrap']/max(1,n):.6f} end={sums['endpoint']/max(1,n):.6f} cont={sums['continuity']/max(1,n):.6f} mean_h={sums['mean_h']/max(1,n):.3f} modeled={sums['modeled_fraction']/max(1,n):.3f}")
        Path(a.out).parent.mkdir(parents=True,exist_ok=True)
        saved_epoch=ep if interrupted else ep+1
        atomic_torch_save({'model':m.state_dict(),'ema':ema.state_dict(),'optimizer':opt.state_dict(),'epoch':saved_epoch,'partial_epoch':(ep+1 if interrupted else None),'partial_batches':(n if interrupted else None),'config':cfg,'preset':a.preset,
                    'latent_ch':latent_ch,'latent_hz':latent_hz,'codec_kind':codec_kind,'codec_sample_rate':codec_sr,
                    'sampling_family':'shortcut','supported_steps':[2**i for i in range(int(math.log2(a.max_steps))+1)],
                    'recommended_steps':int(a.recommend_steps),'max_shortcut_steps':int(a.max_steps),
                    'schema_version':12,'distillation':'string_perceptual_shortcut','source_index':a.index,
                    'training_mix':{'real':a.real_ratio,'modeled':a.modeled_ratio,'modeled_flow_weight':a.modeled_flow_weight,'curriculum':curriculum},'acoustic_promotion_id':promotion_id,'data_fingerprint':data_fingerprint,'recipe_fingerprint':recipe_fingerprint},a.out)
        stop_file=os.environ.get('SONICRAFT_STOP_FILE')
        if interrupted:
            print('[SAFE STOP] partial shortcut epoch saved; epoch',ep+1,'will replay on resume ->',a.out)
            return
        if stop_file and Path(stop_file).exists():
            print('[SAFE STOP] shortcut checkpoint saved at completed epoch',ep+1,'->',a.out)
            return

if __name__=='__main__': main()
