import sys
from pathlib import Path
import torch
from models.ballad_flow_renderer import BalladFlowRenderer

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'runtime'))
from flow_sampler import sample_rectified_flow, midi_authority_base
from model_backend import TorchFlowBackend


def controls(B=2,N=31,dev='cpu'):
    f=lambda v: torch.full((B,N),float(v),device=dev)
    return dict(pitch=f(69),gate=f(1),onset=f(0),velocity=f(.7),dynamics=f(.65),vibrato=f(.5),expression=f(.9),legato=f(1),pitchbend=f(.5),
        transition_speed=f(.5),short_tightness=f(.5),attack_character=f(.38),note_progress=f(.5),phrase_position=f(.5),prev_interval=f(0),next_interval=f(2),
        bow_change_prob=f(.2),vibrato_onset=f(.3),tempo_bpm=f(68),seconds_per_beat=f(60/68),note_duration_beats=f(2),transition_target_ms=f(80),speed_profile=f(0),
        vibrato_depth_cents=f(25),vibrato_rate_hz=f(5.2),vibrato_jitter=f(.03),dynamics_known=f(1),vibrato_known=f(1),expression_known=f(1),legato_known=f(1),pitchbend_known=f(1),timing_known=f(1),articulation_known=f(1),
        instrument=torch.zeros(B,dtype=torch.long,device=dev),articulation=torch.ones(B,dtype=torch.long,device=dev),player=torch.zeros(B,dtype=torch.long,device=dev),articulation_curve=f(1))


def main():
    torch.manual_seed(15); c=controls(); x=torch.randn(2,1024,31,requires_grad=True); t=torch.rand(2)
    legacy=BalladFlowRenderer(d_model=64,layers=2,heads=4)
    dit=BalladFlowRenderer(d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0)
    for name,m in [('legacy',legacy),('dit',dit)]:
        y=m(x,t,**c); assert y.shape==x.shape and torch.isfinite(y).all(); y.square().mean().backward(retain_graph=True)
        print(name,'forward/backward PASS','params',sum(p.numel() for p in m.parameters()))
    with torch.no_grad():
        z=sample_rectified_flow(dit,torch.randn(2,1024,31),c,steps=2,solver='euler',guidance_scale=1.1)
        assert z.shape==(2,1024,31) and torch.isfinite(z).all()
        base=midi_authority_base(c); assert float(base['dynamics'].abs().max())==0.0 and float(base['pitch'].mean())==69.0
    sliced=TorchFlowBackend._slice_controls(c,2.0,5.0,10.0); assert 8 <= sliced['pitch'].shape[1] <= 12
    # v1.4 default topology must retain identical state-dict names/shapes.
    legacy2=BalladFlowRenderer(d_model=64,layers=2,heads=4); legacy2.load_state_dict(legacy.state_dict(),strict=True)
    full_legacy=BalladFlowRenderer(d_model=384,layers=8,heads=8); nano=BalladFlowRenderer(d_model=256,layers=8,heads=8,backbone='adaln_dit',mlp_ratio=2.5,dropout=0.0)
    lp=sum(p.numel() for p in full_legacy.parameters()); np_=sum(p.numel() for p in nano.parameters()); assert np_<lp
    print('sampler/CFG/tile slice/legacy compatibility PASS','legacy_compact',lp,'nano_dit',np_,'reduction',f'{(1-np_/lp)*100:.1f}%')
if __name__=='__main__': main()
