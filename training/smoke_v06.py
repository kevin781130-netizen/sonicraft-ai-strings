import torch
from models.ballad_flow_renderer import BalladFlowRenderer
from models.vibrato_expert import VibratoControlExpert
from tempo_conditioning import transition_target_ms
from vibrato_control import cc3_to_depth_cents, default_vibrato_rate_hz
from tempo_timeline import TempoTimeline

B,T,C=2,32,1024
m=BalladFlowRenderer(latent_ch=C,d_model=64,layers=2,heads=4)
z=torch.randn(B,C,T); t=torch.rand(B)
curve=lambda v: torch.full((B,T),float(v))
args=[curve(64),curve(1),curve(.05),curve(.7),curve(.6),curve(.5),curve(.9),curve(.7),curve(.5),curve(.5),curve(.5),curve(.38),curve(.5),curve(.5),curve(.5),curve(.5),curve(.35),curve(.2),curve(68),curve(60/68),curve(2),curve(80),curve(0),curve(28),curve(5.3),curve(.03),curve(1),curve(1),curve(1),curve(1),curve(0),curve(1),curve(1)]
ins=torch.tensor([0,2]);art=torch.tensor([1,2]);player=torch.tensor([0,3]);art_curve=curve(1)
out=m(z,t,*args,ins,art,player,art_curve);loss=out.square().mean();loss.backward()
assert out.shape==z.shape and torch.isfinite(out).all()
ve=VibratoControlExpert(hidden=32);pred=ve(curve(.5),curve(.6),curve(69),curve(.5),curve(.5),curve(68),curve(2),curve(2/3),ins);assert pred.shape==(B,T,4) and torch.isfinite(pred).all()
assert cc3_to_depth_cents(32) < cc3_to_depth_cents(64) < cc3_to_depth_cents(96) < cc3_to_depth_cents(127)
assert transition_target_ms(56,'legato',.5,'slow') > transition_target_ms(84,'legato',.5,'fast')
assert default_vibrato_rate_hz(.5,69,0,68,'slow') < default_vibrato_rate_hz(.5,69,0,68,'normal') < default_vibrato_rate_hz(.5,69,0,68,'fast')
tl=TempoTimeline([(0,60),(4,90),(8,72)]); assert tl.bpm_at(2)>60 and tl.bpm_at(2)<90 and tl.seconds_between(0,8)>0
print('v0.6 smoke OK', 'renderer_params',sum(p.numel() for p in m.parameters()),'control_dims',m.CONTROL_DIMS,'vib_expert_params',sum(p.numel() for p in ve.parameters()))
