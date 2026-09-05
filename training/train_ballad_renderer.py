from __future__ import annotations
import argparse, copy, json, random
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from models.ballad_flow_renderer import BalladFlowRenderer
from source_policy import validate_index
from string_source_mixer import load_registry, build_mixture_weights, build_curriculum_weights, mixture_audit, coverage_audit
from promotion_binding import promotion_binding

PRESETS = {
    'smoke': {'d_model': 64, 'layers': 2, 'heads': 4},
    'compact': {'d_model': 384, 'layers': 8, 'heads': 8},
    'hq': {'d_model': 512, 'layers': 10, 'heads': 8},
    # MIT-acceleration challengers. They are not promoted until the same held-out/ABX suite wins.
    'compact_dit': {'d_model': 384, 'layers': 8, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 3.0, 'dropout': 0.0},
    'nano_dit': {'d_model': 256, 'layers': 8, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 2.5, 'dropout': 0.0},
    'hq_dit': {'d_model': 512, 'layers': 10, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 3.0, 'dropout': 0.0},
    # v1.6 frontier: intended for a 64-ch / 30 Hz continuous codec. SDPA adds no external runtime dependency.
    'frontier_dit': {'d_model': 192, 'layers': 6, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 2.0, 'dropout': 0.0, 'attention_impl': 'sdpa'},
    'micro_dit': {'d_model': 160, 'layers': 6, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 2.0, 'dropout': 0.0, 'attention_impl': 'sdpa'},
    # v1.7: shared modulation + joint expert fusion remove duplicated matrices without reducing depth.
    'frontier_shared_dit': {'d_model': 192, 'layers': 6, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 2.0, 'dropout': 0.0,
                            'attention_impl': 'sdpa', 'shared_adaln': True, 'interval_conditioning': True, 'expert_fusion': 'joint', 'split_vibrato_validity': True},
    # Aggressive recurrent challenger: same block is unrolled six times. ABX/transition metrics must prove it before promotion.
    'frontier_tied_dit': {'d_model': 192, 'layers': 6, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 2.0, 'dropout': 0.0,
                          'attention_impl': 'sdpa', 'shared_adaln': True, 'weight_tied': True, 'interval_conditioning': True, 'expert_fusion': 'joint', 'split_vibrato_validity': True},
    # v1.8 high-capacity sound teacher: same authority/physics semantics as frontier, but enough capacity to absorb real timbre before distillation.
    'hq_strings_v18': {'d_model': 512, 'layers': 10, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 3.0, 'dropout': 0.0,
                       'attention_impl': 'sdpa', 'shared_adaln': True, 'interval_conditioning': True, 'expert_fusion': 'joint', 'split_vibrato_validity': True},
    # v1.8 frontier core: only ~5K new parameters for hidden quartet/phrase intelligence.
    # The adapter is zero-start and therefore behavior-neutral until quartet fine-tuning.
    'frontier_core_dit': {'d_model': 192, 'layers': 6, 'heads': 8, 'backbone': 'adaln_dit', 'mlp_ratio': 2.0, 'dropout': 0.0,
                          'attention_impl': 'sdpa', 'shared_adaln': True, 'interval_conditioning': True, 'expert_fusion': 'joint', 'split_vibrato_validity': True,
                          'frontier_context_dim': 14, 'context_rank': 24},
}

class Segments(Dataset):
    def __init__(self, index):
        self.rows = [json.loads(x) for x in Path(index).read_text(encoding='utf-8').splitlines() if x.strip()]
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        row = self.rows[i]; d = np.load(row['file'])
        z = torch.from_numpy(d['latent'].astype('float32'))
        ref = d['pitch'].astype('float32'); n = len(ref)
        def curve(name, default):
            return torch.from_numpy(d[name].astype('float32')) if name in d.files else torch.full((n,), float(default))
        base = [curve('pitch',0),curve('gate',0),curve('onset',0),curve('velocity',.7),curve('dynamics',.7),
                curve('vibrato',0),curve('expression',.8),curve('legato',0),curve('pitchbend',0),
                curve('transition_speed',.5),curve('short_tightness',.5),curve('attack_character',.38),
                curve('note_progress',.5),curve('phrase_position',.5),curve('prev_interval',.5),curve('next_interval',.5),
                curve('bow_change_prob',.5),curve('vibrato_onset',.5),
                curve('tempo_bpm',68),curve('seconds_per_beat',60/68),curve('note_duration_beats',2),
                curve('transition_target_ms',80),curve('speed_profile',0),
                curve('vibrato_depth_cents',0),curve('vibrato_rate_hz',5.2),curve('vibrato_jitter',.03),
                curve('dynamics_known',1),curve('vibrato_known',0),curve('vibrato_physics_known',0),curve('expression_known',0),
                curve('legato_known',1),curve('pitchbend_known',0),curve('timing_known',0),curve('articulation_known',1)]
        art_curve = curve('articulation_curve', float(int(d['articulation'])))
        return (z, *base, torch.tensor(int(d['instrument'])), torch.tensor(int(d['articulation'])),
                torch.tensor(int(d['player'])), art_curve, row.get('dataset',''))

def collate(batch):
    cols = list(zip(*batch)); out=[]
    for c in cols[:-1]: out.append(torch.stack(c))
    out.append(list(cols[-1])); return tuple(out)

def source_weights(rows, registry_path='training/dataset_registry.json', real_ratio=.80, modeled_ratio=.20, progress=None):
    registry=load_registry(registry_path) if registry_path else {}
    if progress is None:
        return build_mixture_weights(rows,registry,real_ratio,modeled_ratio)
    return build_curriculum_weights(rows,registry,real_ratio,modeled_ratio,progress=float(progress))

def infer_latent_geometry(ds):
    if not ds.rows: raise RuntimeError('renderer dataset is empty')
    d=np.load(ds.rows[0]['file'],allow_pickle=False)
    latent=d['latent']; ch=int(latent.shape[0])
    def scalar(name, default):
        if name not in d.files: return default
        v=d[name]
        return v.item() if getattr(v,'ndim',0)==0 else v.reshape(-1)[0].item()
    kind=str(scalar('codec_kind','dac44' if ch==1024 else ('strings_vae64' if ch==64 else 'unknown')))
    hz=float(scalar('latent_hz',25.0 if ch==1024 else (30.0 if ch==64 else 0.0)))
    sr=int(scalar('codec_sample_rate',44100 if kind=='dac44' else 48000))
    return ch,hz,kind,sr

@torch.no_grad()
def ema_update(ema, model, decay):
    e=ema.state_dict(); m=model.state_dict()
    for k in e.keys():
        if e[k].dtype.is_floating_point: e[k].mul_(decay).add_(m[k], alpha=1-decay)
        else: e[k].copy_(m[k])

def unpack(vals):
    return vals

def run_batch(model,batch,dev,train=True,cond_dropout=.08,modeled_sources=None,modeled_flow_weight=.35):
    *vals, dsnames = batch
    vals=[x.to(dev,non_blocking=True) for x in vals]
    (z,p,g,o,vel,d,vib,exp,leg,pb,ts,st,ac,np_,phr,pi,ni,bow,vib_on,
     bpm,spb,dur_b,trans_ms,speed_prof,vib_depth,vib_rate,vib_jit,
     dk,vk,vpk,ek,lk,pk,tk,ak,ins,art,player,art_curve)=vals

    if train and cond_dropout>0:
        drop=(torch.rand(z.shape[0],1,device=dev)<cond_dropout).float(); keep=1-drop
        for x in (d,vib,exp,leg,pb,ts,st,ac,bow,vib_on,bpm,spb,dur_b,trans_ms,speed_prof,vib_depth,vib_rate,vib_jit): x.mul_(keep)
        # Keep articulation_known authoritative in the dropped branch. Runtime MIDI-authority
        # CFG never removes the written keyswitch/articulation, so training must expose the same base branch.
        for x in (dk,vk,vpk,ek,lk,pk,tk): x.mul_(keep)

    noise=torch.randn_like(z); t=torch.rand(z.shape[0],device=dev); tt=t[:,None,None]
    xt=(1-tt)*noise+tt*z; target=z-noise
    pred=model(xt,t,p,g,o,vel,d,vib,exp,leg,pb,ts,st,ac,np_,phr,pi,ni,bow,vib_on,
               bpm,spb,dur_b,trans_ms,speed_prof,vib_depth,vib_rate,vib_jit,
               dk,vk,ek,lk,pk,tk,ak,ins,art,player,art_curve, vibrato_physics_known=vpk)

    T=z.shape[-1]
    interp=lambda x: torch.nn.functional.interpolate(x[:,None],size=T,mode='linear',align_corners=False)[:,0]
    on=interp(o).clamp(0,1); lg=interp(leg).clamp(0,1); bw=interp(bow).clamp(0,1)
    vb=interp(vib).clamp(0,1); vk_i=interp(vk).clamp(0,1)
    art_i=torch.nn.functional.interpolate(art_curve[:,None].float(),size=T,mode='nearest')[:,0].long()
    port=(art_i==2).float()
    weight=(1.0 + 1.75*on + 0.50*lg + 0.70*port + 0.30*bw + 0.35*vb*vk_i)[:,None,:]
    per_flow=((pred-target).pow(2)*weight).mean(dim=(1,2))
    modeled_sources=set(modeled_sources or ())
    sample_w=torch.tensor([modeled_flow_weight if str(x).lower() in modeled_sources else 1.0 for x in dsnames],device=dev,dtype=per_flow.dtype)
    flow=(per_flow*sample_w).sum()/sample_w.sum().clamp_min(1e-6)
    dp=pred[...,1:]-pred[...,:-1]; dt=target[...,1:]-target[...,:-1]
    # Continuity/acceleration stay fully supervised: modeled data is allowed to teach transition physics, not timbre.
    continuity=(dp-dt).abs().mean()
    accel=((dp[...,1:]-dp[...,:-1])-(dt[...,1:]-dt[...,:-1])).abs().mean() if T>2 else flow.new_tensor(0.)
    loss=flow+0.085*continuity+0.03*accel
    return loss, {'flow':flow.detach(),'continuity':continuity.detach(),'accel':accel.detach(),'modeled_fraction':(sample_w<1).float().mean().detach()}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--index',default='datasets/processed/ballad_dac/index.jsonl'); ap.add_argument('--val-index')
    ap.add_argument('--out',default='checkpoints/ballad_renderer_last.pt'); ap.add_argument('--best-out',default='checkpoints/ballad_renderer_best.pt')
    ap.add_argument('--epochs',type=int,default=100); ap.add_argument('--batch',type=int,default=2); ap.add_argument('--accum',type=int,default=1)
    ap.add_argument('--preset',choices=PRESETS,default='compact'); ap.add_argument('--registry',default='training/dataset_registry.json')
    ap.add_argument('--resume'); ap.add_argument('--lr',type=float,default=1.5e-4); ap.add_argument('--ema',type=float,default=.999)
    ap.add_argument('--vibrato-expert',default=None,help='Optional supervised VibratoControlExpert checkpoint to seed the exact HQ submodule.')
    ap.add_argument('--performance-experts',default=None,help='Optional supervised Legato/Portamento/Bow PerformanceExperts checkpoint to seed the exact HQ submodule.')
    ap.add_argument('--expert-freeze-epochs',type=int,default=12,help='Warm-up epochs to preserve calibrated expert weights before end-to-end fine-tuning.')
    ap.add_argument('--cond-dropout',type=float,default=.08); ap.add_argument('--seed',type=int,default=1337)
    ap.add_argument('--latent-ch',type=int,default=0,help='0 = infer from first latent NPZ')
    ap.add_argument('--latent-hz',type=float,default=0.0,help='0 = infer from NPZ/profile')
    ap.add_argument('--codec-kind',default='auto'); ap.add_argument('--codec-sample-rate',type=int,default=0)
    ap.add_argument('--real-ratio',type=float,default=.80); ap.add_argument('--modeled-ratio',type=float,default=.20)
    ap.add_argument('--modeled-flow-weight',type=float,default=.35,help='Down-weight modeled latent endpoint/timbre loss while keeping modeled transition losses active.')
    ap.add_argument('--acoustic-promotion',help='Passed v2.0 acoustic_promotion.json; binds checkpoint to exact promotion evidence.')
    a=ap.parse_args(); promotion_id,curriculum=promotion_binding(a.acoustic_promotion); random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    validate_index(a.index,a.registry)
    if a.val_index: validate_index(a.val_index,a.registry)
    dev='cuda' if torch.cuda.is_available() else 'cpu'; ds=Segments(a.index)
    inferred_ch,inferred_hz,inferred_kind,inferred_sr=infer_latent_geometry(ds)
    latent_ch=int(a.latent_ch or inferred_ch); latent_hz=float(a.latent_hz or inferred_hz)
    codec_kind=inferred_kind if str(a.codec_kind).lower()=='auto' else str(a.codec_kind)
    codec_sample_rate=int(a.codec_sample_rate or inferred_sr)
    if latent_ch!=inferred_ch: raise RuntimeError(f'latent channel override {latent_ch} != dataset {inferred_ch}')
    registry=load_registry(a.registry); mix_w=source_weights(ds.rows,a.registry,a.real_ratio,a.modeled_ratio)
    print('renderer string mixture',json.dumps(mixture_audit(ds.rows,mix_w,registry),sort_keys=True))
    print('renderer coverage curriculum',json.dumps(coverage_audit(ds.rows,mix_w,registry),sort_keys=True))
    modeled_sources={str(k).lower() for k,v in registry.items() if str(v.get('training_origin','real')).lower()=='modeled'}
    sampler=WeightedRandomSampler(mix_w,max(len(ds),128),replacement=True)
    dl=DataLoader(ds,batch_size=a.batch,sampler=sampler,num_workers=0,pin_memory=torch.cuda.is_available(),collate_fn=collate)
    vdl=None
    if a.val_index:
        vds=Segments(a.val_index); vdl=DataLoader(vds,batch_size=a.batch,shuffle=False,num_workers=0,collate_fn=collate)

    cfg=dict(PRESETS[a.preset]); m=BalladFlowRenderer(latent_ch=latent_ch,**cfg).to(dev)
    expert_loaded=False
    if a.vibrato_expert and Path(a.vibrato_expert).exists():
        eck=torch.load(a.vibrato_expert,map_location='cpu'); m.vibrato_physics.load_state_dict(eck['model'],strict=True)
        expert_loaded=True; print('loaded supervised vibrato expert',a.vibrato_expert)
    elif a.vibrato_expert:
        print('[INFO] vibrato expert checkpoint not found; HQ will train its submodule end-to-end:',a.vibrato_expert)
    if a.performance_experts and Path(a.performance_experts).exists():
        eck=torch.load(a.performance_experts,map_location='cpu'); m.performance_experts.load_state_dict(eck['model'],strict=True)
        expert_loaded=True; print('loaded supervised performance experts',a.performance_experts)
    elif a.performance_experts:
        print('[INFO] performance expert checkpoint not found; HQ will train its submodule end-to-end:',a.performance_experts)
    ema=copy.deepcopy(m).eval().requires_grad_(False)
    opt=torch.optim.AdamW(m.parameters(),a.lr,weight_decay=.01,betas=(.9,.95)); sched=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=max(1,a.epochs),eta_min=a.lr*.08)
    start=0; best=float('inf')
    if a.resume:
        ck=torch.load(a.resume,map_location='cpu'); saved=ck.get('config',{})
        if any(saved.get(k)!=cfg[k] for k in cfg): raise RuntimeError('Resume checkpoint architecture mismatch.')
        if int(ck.get('latent_ch',latent_ch))!=latent_ch: raise RuntimeError('Resume checkpoint latent geometry mismatch.')
        m.load_state_dict(ck['model']); ema.load_state_dict(ck.get('ema',ck['model']))
        if 'optimizer' in ck: opt.load_state_dict(ck['optimizer'])
        if 'scheduler' in ck: sched.load_state_dict(ck['scheduler'])
        start=int(ck.get('epoch',0)); best=float(ck.get('best_val',best)); print('resumed',a.resume,'at',start)

    expert_modules=(m.vibrato_physics,m.performance_experts)
    def set_expert_trainable(flag: bool):
        for mod in expert_modules:
            for param in mod.parameters(): param.requires_grad_(flag)
    if expert_loaded and a.expert_freeze_epochs>0:
        set_expert_trainable(False); print('freezing calibrated physical experts for',a.expert_freeze_epochs,'warm-up epochs')

    use_amp=(dev=='cuda' and torch.cuda.is_bf16_supported())
    ampctx=lambda: torch.autocast(device_type='cuda',dtype=torch.bfloat16,enabled=use_amp)
    print('renderer params',sum(p.numel() for p in m.parameters()),'device',dev,'segments',len(ds),cfg,'controls',m.CONTROL_DIMS,'bf16',use_amp,
          'codec',codec_kind,'latent',latent_ch,'@',latent_hz,'Hz')

    for ep in range(start,start+a.epochs):
        progress=(ep-start)/max(1,a.epochs-1)
        sampler.weights=torch.as_tensor(source_weights(ds.rows,a.registry,a.real_ratio,a.modeled_ratio,progress=progress),dtype=torch.double)
        if expert_loaded and a.expert_freeze_epochs>0 and ep==start+a.expert_freeze_epochs:
            set_expert_trainable(True); print('unfroze physical experts for end-to-end HQ refinement')
        m.train(); opt.zero_grad(set_to_none=True); sums={'flow':0.,'continuity':0.,'accel':0.,'modeled_fraction':0.}; steps=0
        for bi,batch in enumerate(dl):
            with ampctx(): loss,met=run_batch(m,batch,dev,True,a.cond_dropout,modeled_sources,a.modeled_flow_weight); loss=loss/a.accum
            loss.backward()
            if (bi+1)%a.accum==0:
                torch.nn.utils.clip_grad_norm_(m.parameters(),1.0); opt.step(); opt.zero_grad(set_to_none=True); ema_update(ema,m,a.ema)
            for k,v in met.items(): sums[k]+=float(v)
            steps+=1
        sched.step(); denom=max(1,steps)
        msg=f"epoch {ep+1:03d} train_flow={sums['flow']/denom:.6f} cont={sums['continuity']/denom:.6f} accel={sums['accel']/denom:.6f} modeled={sums['modeled_fraction']/denom:.3f} lr={sched.get_last_lr()[0]:.2e}"
        val=float('nan')
        if vdl:
            ema.eval(); vals=[]
            with torch.no_grad():
                for batch in vdl:
                    with ampctx(): _,met=run_batch(ema,batch,dev,False,0,modeled_sources,a.modeled_flow_weight); vals.append(float(met['flow']))
            val=sum(vals)/max(1,len(vals)); msg+=f' val_flow={val:.6f}'
        print(msg)
        ck={'model':m.state_dict(),'ema':ema.state_dict(),'optimizer':opt.state_dict(),'scheduler':sched.state_dict(),
            'epoch':ep+1,'config':cfg,'preset':a.preset,'latent_ch':latent_ch,'latent_hz':latent_hz,
            'codec_kind':codec_kind,'codec_sample_rate':codec_sample_rate,'articulations':12,
            'control_dims':m.CONTROL_DIMS,'source_index':a.index,'val_index':a.val_index,'best_val':best,'schema_version':9,
            'vibrato_expert_seed':a.vibrato_expert,'performance_experts_seed':a.performance_experts,
            'training_mix':{'real':a.real_ratio,'modeled':a.modeled_ratio,'modeled_flow_weight':a.modeled_flow_weight,'curriculum':curriculum},
            'acoustic_promotion_id':promotion_id}
        Path(a.out).parent.mkdir(parents=True,exist_ok=True); torch.save(ck,a.out)
        score=val if vdl else sums['flow']/denom
        if score<best:
            best=score; ck['best_val']=best; torch.save(ck,a.best_out)

if __name__=='__main__': main()
