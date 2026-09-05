from __future__ import annotations
import math, tempfile
from pathlib import Path
import sys
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from string_source_mixer import build_mixture_weights, build_curriculum_weights, mixture_audit, coverage_audit
from dataclasses import replace
from cleanroom_bowed_synth import random_controls, synthesize, synthesize_section
from models.string_physics_probe import StringPhysicsProbe, physics_targets, masked_physics_loss
from models.string_vae64 import StringVAE64
from models.stft_discriminator import MultiResolutionSTFTDiscriminator, discriminator_hinge


def main():
    registry={
        'real_a':{'training_origin':'real'},
        'real_b':{'training_origin':'real'},
        'synthetic_cleanroom_bowed_v18':{'training_origin':'modeled'},
    }
    rows=[{'dataset':'real_a'} for _ in range(7)]+[{'dataset':'real_b'} for _ in range(3)]+[
        {'dataset':'synthetic_cleanroom_bowed_v18','training_origin':'modeled'} for _ in range(40)]
    w=build_mixture_weights(rows,registry,.8,.2,require_modeled=True)
    a=mixture_audit(rows,w,registry)
    assert abs(a['real_probability']-.8)<1e-7, a
    assert abs(a['modeled_probability']-.2)<1e-7, a
    # Curriculum may redistribute quality/rare-technique mass inside lanes, but must never move the 80/20 boundary.
    tagged=[]
    for i,r in enumerate(rows):
        rr=dict(r); rr['instrument']=i%4; rr['articulation']=i%12; tagged.append(rr)
    for progress in (0.0,.5,1.0):
        cw=build_curriculum_weights(tagged,registry,.8,.2,progress=progress,require_modeled=True)
        ca=mixture_audit(tagged,cw,registry); cov=coverage_audit(tagged,cw,registry)
        assert abs(ca['real_probability']-.8)<1e-7 and abs(ca['modeled_probability']-.2)<1e-7, (progress,ca)
        assert cov['known_cells']>0

    rng=np.random.default_rng(8); c=random_controls(rng,0,0); x=synthesize(c,seconds=.10,sample_rate=48000,seed=8)
    assert x.shape==(4800,) and np.isfinite(x).all() and np.max(np.abs(x))<=1.0001

    probe=StringPhysicsProbe(64,16)
    z=torch.randn(2,64,5,requires_grad=True)
    prows=[c.manifest(),{'dataset':'real_a'}]
    target,mask=physics_targets(prows)
    pred=probe(z); loss=masked_physics_loss(pred,target,mask)
    loss.backward()
    assert torch.isfinite(loss) and z.grad is not None and torch.isfinite(z.grad).all()
    assert mask[0].sum()==12 and mask[1].sum()==0

    # Section clean-room teacher: multi-player texture with exact dispersion labels, still training_origin=modeled.
    cs=replace(c,section_players=4,section_pitch_spread_cents=6.0,section_timing_spread_ms=9.0,section_bow_spread=.08)
    xs=synthesize_section(cs,seconds=.10,sample_rate=48000,seed=18)
    assert xs.shape==x.shape and np.isfinite(xs).all() and np.max(np.abs(xs))<=1.0001 and not np.array_equal(xs,x)
    sm=cs.manifest(); assert sm['section_pitch_spread_cents_known']==1.0 and sm['section_timing_spread_ms_known']==1.0

    codec=StringVAE64(channels=4)
    full={'model':codec.state_dict(),'physics_probe':probe.state_dict()}
    consumer={'decoder':codec.decoder.state_dict()}
    assert 'physics_probe' in full and 'physics_probe' not in consumer
    assert not any('encoder' in k for k in consumer['decoder'])

    # Training-only pitch/log-frequency critic must accept short 48 kHz strings and backpropagate.
    disc=MultiResolutionSTFTDiscriminator(resolutions=((256,64),(512,128)),base=4,include_log_frequency=True)
    real=torch.from_numpy(x[:4096]).view(1,1,-1).float()
    fake=(real*.95).requires_grad_(True)
    dloss=discriminator_hinge(disc(real),disc(fake))
    dloss.backward(); assert fake.grad is not None and torch.isfinite(fake.grad).all()
    print('v1.8 REAL80/MODEL20 smoke PASS',
          'real_prob',round(a['real_probability'],3),'modeled_prob',round(a['modeled_probability'],3),
          'probe_params',sum(p.numel() for p in probe.parameters()),'cleanroom_peak',float(np.max(np.abs(x))),'section_peak',float(np.max(np.abs(xs))))

if __name__=='__main__': main()
