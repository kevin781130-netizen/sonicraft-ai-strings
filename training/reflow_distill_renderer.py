from __future__ import annotations
"""Reflow distillation for fewer runtime ODE steps.

The teacher first maps noise -> a conditioned endpoint. The student then learns the
straight velocity between that exact noise/endpoint pair, while an optional real-data
anchor prevents teacher errors from becoming the only target. This is training-only;
it adds zero release-model parameters.
"""
import argparse, copy, sys, json
from pathlib import Path
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler
from models.ballad_flow_renderer import BalladFlowRenderer
from train_ballad_renderer import Segments, collate, source_weights, PRESETS, ema_update
from promotion_binding import promotion_binding
from source_policy import validate_index
from string_source_mixer import load_registry, build_curriculum_weights, mixture_audit

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime'
if str(RUNTIME) not in sys.path: sys.path.insert(0,str(RUNTIME))
from flow_sampler import sample_rectified_flow

CONTROL_NAMES=(
    'pitch','gate','onset','velocity','dynamics','vibrato','expression','legato','pitchbend',
    'transition_speed','short_tightness','attack_character','note_progress','phrase_position',
    'prev_interval','next_interval','bow_change_prob','vibrato_onset','tempo_bpm','seconds_per_beat',
    'note_duration_beats','transition_target_ms','speed_profile','vibrato_depth_cents','vibrato_rate_hz',
    'vibrato_jitter','dynamics_known','vibrato_known','vibrato_physics_known','expression_known','legato_known','pitchbend_known',
    'timing_known','articulation_known','instrument','articulation','player','articulation_curve'
)

def split_batch(batch,dev):
    *vals,dsnames=batch
    vals=[x.to(dev,non_blocking=True) for x in vals]
    z=vals[0]; controls=dict(zip(CONTROL_NAMES,vals[1:]))
    return z,controls,dsnames

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--index',default='datasets/processed/ballad_dac/index.jsonl')
    ap.add_argument('--teacher',required=True); ap.add_argument('--out',default='checkpoints/reflow_nano_dit.pt')
    ap.add_argument('--student-preset',choices=PRESETS,default='nano_dit')
    ap.add_argument('--teacher-steps',type=int,default=24); ap.add_argument('--target-steps',type=int,default=4)
    ap.add_argument('--epochs',type=int,default=30); ap.add_argument('--batch',type=int,default=1); ap.add_argument('--accum',type=int,default=1)
    ap.add_argument('--lr',type=float,default=1.0e-4); ap.add_argument('--anchor',type=float,default=.20)
    ap.add_argument('--registry',default='training/dataset_registry.json'); ap.add_argument('--ema',type=float,default=.999)
    ap.add_argument('--real-ratio',type=float,default=.80); ap.add_argument('--modeled-ratio',type=float,default=.20); ap.add_argument('--modeled-flow-weight',type=float,default=.35)
    ap.add_argument('--acoustic-promotion')
    a=ap.parse_args(); promotion_id,curriculum=promotion_binding(a.acoustic_promotion); validate_index(a.index,a.registry)
    dev='cuda' if torch.cuda.is_available() else 'cpu'; ds=Segments(a.index)
    registry=load_registry(a.registry); weights=build_curriculum_weights(ds.rows,registry,a.real_ratio,a.modeled_ratio,progress=0.0)
    print('reflow string mixture',json.dumps(mixture_audit(ds.rows,weights,registry),sort_keys=True))
    modeled_sources={str(k).lower() for k,v in registry.items() if str(v.get('training_origin','real')).lower()=='modeled'}
    sampler=WeightedRandomSampler(weights,max(len(ds),128),replacement=True)
    dl=DataLoader(ds,batch_size=a.batch,sampler=sampler,collate_fn=collate,num_workers=0,pin_memory=torch.cuda.is_available())

    tck=torch.load(a.teacher,map_location='cpu'); tcfg=dict(tck.get('config') or {})
    teacher=BalladFlowRenderer(latent_ch=int(tck.get('latent_ch',1024)),**tcfg).to(dev).eval()
    teacher.load_state_dict(tck.get('ema',tck['model']),strict=True); teacher.requires_grad_(False)
    latent_ch=int(tck.get('latent_ch',1024)); scfg=dict(PRESETS[a.student_preset]); student=BalladFlowRenderer(latent_ch=latent_ch,**scfg).to(dev)
    ema=copy.deepcopy(student).eval().requires_grad_(False)
    opt=torch.optim.AdamW(student.parameters(),a.lr,weight_decay=.01,betas=(.9,.95))
    use_amp=(dev=='cuda' and torch.cuda.is_bf16_supported())
    ampctx=lambda: torch.autocast(device_type='cuda',dtype=torch.bfloat16,enabled=use_amp)
    print('reflow teacher',tcfg,'student',a.student_preset,scfg,'teacher_steps',a.teacher_steps,'target_steps',a.target_steps)

    for ep in range(a.epochs):
        progress=ep/max(1,a.epochs-1); sampler.weights=torch.as_tensor(build_curriculum_weights(ds.rows,registry,a.real_ratio,a.modeled_ratio,progress=progress),dtype=torch.double)
        student.train(); total=straight_total=anchor_total=transition_total=0.; n=0; opt.zero_grad(set_to_none=True)
        for bi,batch in enumerate(dl):
            z,controls,dsnames=split_batch(batch,dev); z0=torch.randn_like(z)
            with torch.no_grad(), ampctx():
                endpoint=sample_rectified_flow(teacher,z0,controls,steps=a.teacher_steps,solver='euler',guidance_scale=1.0)
            t=torch.rand(z.shape[0],device=dev); tt=t[:,None,None]
            xt=(1-tt)*z0+tt*endpoint; target=endpoint-z0
            with ampctx():
                pred=student(xt,t,**controls); straight_per=(pred-target).pow(2).mean(dim=(1,2))
                sw=torch.tensor([a.modeled_flow_weight if str(x).lower() in modeled_sources else 1.0 for x in dsnames],device=dev,dtype=straight_per.dtype)
                straight=(straight_per*sw).sum()/sw.sum().clamp_min(1e-6)
                transition=((pred[...,1:]-pred[...,:-1])-(target[...,1:]-target[...,:-1])).abs().mean() if pred.shape[-1]>1 else straight.new_tensor(0.)
                # Real-data anchor uses an independent path so the distilled model remains tied
                # to the measured latent distribution instead of inheriting only teacher bias.
                if a.anchor>0:
                    n0=torch.randn_like(z); ta=torch.rand(z.shape[0],device=dev); tta=ta[:,None,None]
                    xa=(1-tta)*n0+tta*z; ya=z-n0
                    anchor_pred=student(xa,ta,**controls)
                    anchor_per=(anchor_pred-ya).pow(2).mean(dim=(1,2))
                    anchor=(anchor_per*sw).sum()/sw.sum().clamp_min(1e-6)
                else: anchor=straight.new_tensor(0.)
                loss=straight+float(a.anchor)*anchor+.05*transition
            (loss/a.accum).backward()
            if (bi+1)%a.accum==0:
                torch.nn.utils.clip_grad_norm_(student.parameters(),1.0); opt.step(); opt.zero_grad(set_to_none=True); ema_update(ema,student,a.ema)
            total+=float(loss.detach()); straight_total+=float(straight.detach()); anchor_total+=float(anchor.detach()); transition_total+=float(transition.detach()); n+=1
        print(f'epoch {ep+1:03d} reflow={total/max(1,n):.6f} straight={straight_total/max(1,n):.6f} anchor={anchor_total/max(1,n):.6f} transition={transition_total/max(1,n):.6f}')
        Path(a.out).parent.mkdir(parents=True,exist_ok=True)
        torch.save({'model':student.state_dict(),'ema':ema.state_dict(),'epoch':ep+1,'config':scfg,'preset':a.student_preset,
                    'latent_ch':latent_ch,'latent_hz':float(tck.get('latent_hz',25.0)),'codec_kind':tck.get('codec_kind','dac44'),
                    'codec_sample_rate':int(tck.get('codec_sample_rate',44100)),'teacher':a.teacher,'teacher_steps':a.teacher_steps,'recommended_steps':a.target_steps,
                    'anchor':a.anchor,'schema_version':10,'distillation':'reflow',
                    'training_mix':{'real':a.real_ratio,'modeled':a.modeled_ratio,'modeled_flow_weight':a.modeled_flow_weight,'curriculum':curriculum},'acoustic_promotion_id':promotion_id},a.out)

if __name__=='__main__': main()
