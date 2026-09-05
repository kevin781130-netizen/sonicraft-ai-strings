from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime')); sys.path.insert(0,str(ROOT/'training'))
from models.ballad_flow_renderer import BalladFlowRenderer
from models.string_vae64 import StringVAE64
from flow_sampler import sample_shortcut_flow, midi_authority_base
from model_backend import TorchFlowBackend
from frontier_context import frontier_context_curves, phrase_position_curve
from shortcut_distill_renderer import shortcut_losses


def controls(B=1,N=30,ctx=False):
    f=lambda v: torch.full((B,N),float(v))
    d=dict(pitch=f(69),gate=f(1),onset=f(0),velocity=f(.7),dynamics=f(.65),vibrato=f(.5),expression=f(.9),legato=f(1),pitchbend=f(.5),
        transition_speed=f(.5),short_tightness=f(.5),attack_character=f(.38),note_progress=f(.5),phrase_position=f(.5),prev_interval=f(0),next_interval=f(2),
        bow_change_prob=f(.2),vibrato_onset=f(.3),tempo_bpm=f(68),seconds_per_beat=f(60/68),note_duration_beats=f(2),transition_target_ms=f(80),speed_profile=f(0),
        vibrato_depth_cents=f(25),vibrato_rate_hz=f(5.2),vibrato_jitter=f(.03),dynamics_known=f(1),vibrato_known=f(1),expression_known=f(1),legato_known=f(1),pitchbend_known=f(1),timing_known=f(1),articulation_known=f(1),vibrato_physics_known=f(0),
        instrument=torch.zeros(B,dtype=torch.long),articulation=torch.ones(B,dtype=torch.long),player=torch.zeros(B,dtype=torch.long),articulation_curve=f(1))
    if ctx:d['frontier_context']=torch.zeros(B,14,N)
    return d


def main():
    torch.manual_seed(18)
    old_cfg=dict(latent_ch=64,d_model=192,layers=6,heads=8,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0,attention_impl='sdpa',shared_adaln=True,interval_conditioning=True,expert_fusion='joint',split_vibrato_validity=True)
    core_cfg=dict(old_cfg,frontier_context_dim=14,context_rank=24)
    old=BalladFlowRenderer(**old_cfg); core=BalladFlowRenderer(**core_cfg)
    old_p=sum(p.numel() for p in old.parameters()); core_p=sum(p.numel() for p in core.parameters()); delta=core_p-old_p
    assert 0<delta<10000,delta

    x=torch.randn(1,64,30); t=torch.tensor([.35]); h=torch.tensor([.5]); c=controls(ctx=True)
    # Zero-start context adapter must be a no-op before quartet fine-tuning.
    with torch.no_grad(): y0=core(x,t,flow_h=h,**c)
    c1=controls(ctx=True); c1['frontier_context'].normal_()
    with torch.no_grad(): y1=core(x,t,flow_h=h,**c1)
    assert torch.equal(y0,y1)
    # Once trained, the same tiny adapter is capable of changing hidden realization.
    with torch.no_grad(): core.frontier_context.up.weight[0,0]=.1
    y2=core(x,t,flow_h=h,**c1); assert not torch.equal(y1,y2); y2.square().mean().backward()

    # Training-only perceptual shortcut objective stays finite and includes endpoint protection.
    tiny=BalladFlowRenderer(latent_ch=64,d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.,attention_impl='sdpa',shared_adaln=True,interval_conditioning=True,expert_fusion='joint',split_vibrato_validity=True,frontier_context_dim=14,context_rank=12)
    ema=BalladFlowRenderer(latent_ch=64,d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.,attention_impl='sdpa',shared_adaln=True,interval_conditioning=True,expert_fusion='joint',split_vibrato_validity=True,frontier_context_dim=14,context_rank=12)
    ema.load_state_dict(tiny.state_dict(),strict=True); ema.eval().requires_grad_(False)
    loss,met=shortcut_losses(tiny,ema,torch.randn(1,64,30),controls(ctx=True),4,0.0)
    assert torch.isfinite(loss) and 'endpoint' in met and torch.isfinite(met['endpoint']); loss.backward()

    # Phrase look-back: a note starting before the render window remains gated but does not create a fake onset.
    sr=48000; start=sr*4; end=sr*6
    base_ctrl=[.65,.5,.9,1.,.5,0.,1.,.1,.5,1/11,.5,.5,.38,0.]
    ev=[
      {'project_sample':sr*3,'type':1,'part':0,'note':69,'articulation':1,'velocity':.7,'tempo_bpm':60.,'controls':base_ctrl},
      {'project_sample':sr*5,'type':2,'part':0,'note':69,'articulation':1,'velocity':0.,'tempo_bpm':60.,'controls':base_ctrl},
      {'project_sample':sr*4,'type':1,'part':1,'note':64,'articulation':1,'velocity':.7,'tempo_bpm':60.,'controls':base_ctrl},
    ]
    ctx,phrase=frontier_context_curves(ev,0,start,end,sr,60.,fps=100)
    assert ctx.shape==(14,200) and phrase.shape==(200,) and phrase[0]>0
    backend=TorchFlowBackend(Path('.')); backend.torch=torch; backend.device='cpu'
    req=SimpleNamespace(sample_rate=sr,start_sample=start,end_sample=end,tempo_bpm=60.,flags=2)
    cc=backend._build_part_controls(req,ev,0)
    assert float(cc['gate'][0,0])==1.0 and float(cc['onset'][0,0])==0.0 and tuple(cc['frontier_context'].shape)==(1,14,200)

    # Context is expressive-only in CFG base; score trajectory remains present.
    base=midi_authority_base(cc); assert float(base['pitch'].max())==69. and float(base['frontier_context'].abs().max())==0.

    # 1-step consumer path still uses one renderer network.
    with torch.no_grad(): out=sample_shortcut_flow(core,torch.randn(1,64,30),controls(ctx=True),steps=1)
    assert out.shape==(1,64,30) and torch.isfinite(out).all()

    vae=StringVAE64(channels=16); dec_p=sum(p.numel() for p in vae.decoder.parameters())
    print('v1.8 frontier context/phrase lookback/perceptual-shortcut PASS')
    print('v17_shared',old_p,'v18_core',core_p,'context_delta',delta)
    print('v18 core+decoder FP16 MiB',f'{(core_p+dec_p)*2/2**20:.2f}')

if __name__=='__main__': main()
