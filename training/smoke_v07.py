import tempfile, json
from pathlib import Path
import numpy as np, torch
from models.ballad_flow_renderer import BalladFlowRenderer
from models.vibrato_expert import VibratoControlExpert
from models.performance_experts import PerformanceExperts
from performance_timing import TimingCalibration,target_transition
from vibrato_control import cc3_to_depth_cents,default_vibrato_rate_hz

B,T,C=2,40,1024
curve=lambda v: torch.full((B,T),float(v))
z=torch.randn(B,C,T);t=torch.rand(B)
m=BalladFlowRenderer(latent_ch=C,d_model=64,layers=2,heads=4)
args=[curve(64),curve(1),curve(.05),curve(.7),curve(.6),curve(.5),curve(.9),curve(.7),curve(.5),
      curve(.5),curve(.5),curve(.38),curve(.5),curve(.5),curve(2),curve(-2),curve(.35),curve(.2),
      curve(68),curve(60/68),curve(2),curve(84),curve(2/3),curve(28),curve(5.3),curve(.03),
      curve(1),curve(1),curve(1),curve(1),curve(0),curve(1),curve(1)]
ins=torch.tensor([0,2]);art=torch.tensor([1,2]);player=torch.tensor([0,3]);art_curve=torch.cat([curve(1)[:1],curve(2)[:1]],0)
out=m(z,t,*args,ins,art,player,art_curve);loss=out.square().mean();loss.backward()
assert out.shape==z.shape and torch.isfinite(out).all()
assert m.CONTROL_DIMS==34
assert isinstance(m.vibrato_physics,VibratoControlExpert)
assert isinstance(m.performance_experts,PerformanceExperts)

ve=VibratoControlExpert(hidden=32);vp=ve(curve(.5),curve(.6),curve(69),curve(.5),curve(.5),curve(68),curve(2),curve(2/3),ins)
assert vp.shape==(B,T,4) and torch.isfinite(vp).all()
pe=PerformanceExperts(hidden=32);pp=pe(curve(64),curve(.6),curve(.5),curve(.5),curve(2),curve(-2),curve(68),curve(2),curve(.5),curve(.5),curve(.38),curve(1),curve(.7),ins)
for k in ('legato','portamento','bow'):
    assert pp[k].shape==(B,T,4) and torch.isfinite(pp[k]).all()
(sum(x.square().mean() for x in pp.values())).backward()

# CC3 has four active non-zero layers plus straight, and depth remains independent from rate selection.
assert cc3_to_depth_cents(0)==0
assert cc3_to_depth_cents(32)<cc3_to_depth_cents(64)<cc3_to_depth_cents(96)<cc3_to_depth_cents(127)
assert default_vibrato_rate_hz(.5,69,0,68,'slow')<default_vibrato_rate_hz(.5,69,0,68,'normal')<default_vibrato_rate_hz(.5,69,0,68,'fast')

cal=TimingCalibration.default()
for fam in ('legato','portamento','bow_change'):
    slow=target_transition(68,fam,.5,'slow',0,cal);normal=target_transition(68,fam,.5,'normal',0,cal);fast=target_transition(68,fam,.5,'fast',0,cal)
    assert slow['transition_ms']>normal['transition_ms']>fast['transition_ms']
# Same musical profile becomes shorter in milliseconds when song tempo is faster.
assert target_transition(56,'legato',.5,'normal',0,cal)['transition_ms']>target_transition(96,'legato',.5,'normal',0,cal)['transition_ms']
print('v0.7 smoke OK','renderer_params',sum(p.numel() for p in m.parameters()),'control_dims',m.CONTROL_DIMS,
      'perf_expert_params',sum(p.numel() for p in pe.parameters()))
