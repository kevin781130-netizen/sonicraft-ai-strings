from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
sys.path.insert(0,str(ROOT/'training'))
from models.ballad_flow_renderer import BalladFlowRenderer
from models.string_vae64 import StringVAE64
from flow_sampler import sample_rectified_flow, sample_shortcut_flow
from model_backend import TorchFlowBackend
from release_integrity import verify_release_manifest
from quartet_interaction import coordinate_hidden_ensemble
from tile_cache import AudioTileCache
from shortcut_distill_renderer import shortcut_losses


def controls(B=1,N=30,dev='cpu'):
    f=lambda v: torch.full((B,N),float(v),device=dev)
    return dict(pitch=f(69),gate=f(1),onset=f(0),velocity=f(.7),dynamics=f(.65),vibrato=f(.5),expression=f(.9),legato=f(1),pitchbend=f(.5),
        transition_speed=f(.5),short_tightness=f(.5),attack_character=f(.38),note_progress=f(.5),phrase_position=f(.5),prev_interval=f(0),next_interval=f(2),
        bow_change_prob=f(.2),vibrato_onset=f(.3),tempo_bpm=f(68),seconds_per_beat=f(60/68),note_duration_beats=f(2),transition_target_ms=f(80),speed_profile=f(0),
        vibrato_depth_cents=f(25),vibrato_rate_hz=f(5.2),vibrato_jitter=f(.03),dynamics_known=f(1),vibrato_known=f(1),expression_known=f(1),legato_known=f(1),pitchbend_known=f(1),timing_known=f(1),articulation_known=f(1),vibrato_physics_known=f(0),
        instrument=torch.zeros(B,dtype=torch.long,device=dev),articulation=torch.ones(B,dtype=torch.long,device=dev),player=torch.zeros(B,dtype=torch.long,device=dev),articulation_curve=f(1))


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def integrity_smoke():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for n in ('frontier.pt','hq.pt','decoder.pt','training_provenance.json','release_metrics.json'):
            (td/n).write_bytes(b'v17-'+n.encode())
        m={'schema':4,'product':'SONICRAFT AI Strings Q4','version':'1.7.0-frontier-exit','commercial_safe':True,'release_approved':True,'profile':'full_hq',
           'codec':{'kind':'strings_vae64','sample_rate':48000,'latent_ch':64,'latent_hz':30.0,'downsampling_ratio':1600},
           'sampler':{'family':'shortcut','supported_steps':[1,2,4,8],'recommended_steps':2,'interval_conditioning':True},
           'files':[{'name':'frontier.pt','role':'compact','sha256':sha(td/'frontier.pt')},{'name':'hq.pt','role':'hq','sha256':sha(td/'hq.pt')},{'name':'decoder.pt','role':'string_vae64','sha256':sha(td/'decoder.pt')}],
           'provenance':{'file':'training_provenance.json','sha256':sha(td/'training_provenance.json'),'contains_blocked_sources':False},
           'metrics':{'file':'release_metrics.json','sha256':sha(td/'release_metrics.json')}}
        (td/'release_model_manifest.json').write_text(json.dumps(m),encoding='utf-8')
        got=verify_release_manifest(td); assert got['verified'] and got['manifest']['_capabilities']['codec']=='strings_vae64'


def main():
    torch.manual_seed(17)
    # Codec geometry remains 48k / 1600x / 64d. Consumer only needs the decoder.
    vae=StringVAE64(channels=16)
    wav=torch.randn(1,1,3200,requires_grad=True); rec,mu,lv=vae(wav,sample=False)
    assert mu.shape==(1,64,2) and rec.shape==wav.shape
    (rec.square().mean()+1e-5*(mu.square()+lv.square()).mean()).backward()
    dec_p=sum(p.numel() for p in vae.decoder.parameters())

    # Legacy state layouts still strict-load.
    legacy=BalladFlowRenderer(d_model=64,layers=2,heads=4)
    BalladFlowRenderer(d_model=64,layers=2,heads=4).load_state_dict(legacy.state_dict(),strict=True)
    dit15=BalladFlowRenderer(d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0)
    BalladFlowRenderer(d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0,attention_impl='mha').load_state_dict(dit15.state_dict(),strict=True)

    cfg_shared=dict(latent_ch=64,d_model=192,layers=6,heads=8,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0,attention_impl='sdpa',shared_adaln=True,interval_conditioning=True,expert_fusion='joint',split_vibrato_validity=True)
    cfg_tied=dict(cfg_shared,weight_tied=True)
    shared=BalladFlowRenderer(**cfg_shared); tied=BalladFlowRenderer(**cfg_tied); shared.latent_hz=30.0; tied.latent_hz=30.0
    c=controls(); x=torch.randn(1,64,30,requires_grad=True); t=torch.rand(1); h=torch.full((1,),.25)
    y=shared(x,t,flow_h=h,**c); assert y.shape==x.shape and torch.isfinite(y).all(); y.square().mean().backward()
    xt=torch.randn(1,64,30,requires_grad=True); yt=tied(xt,t,flow_h=h,**c); assert yt.shape==xt.shape; yt.square().mean().backward()
    shared_p=sum(p.numel() for p in shared.parameters()); tied_p=sum(p.numel() for p in tied.parameters())
    frontier16=BalladFlowRenderer(latent_ch=64,d_model=192,layers=6,heads=8,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0,attention_impl='sdpa')
    old_p=sum(p.numel() for p in frontier16.parameters()); assert tied_p<shared_p<old_p

    # Same shipping network can be evaluated at 1/2 steps when interval-conditioned.
    with torch.no_grad():
        z1=sample_shortcut_flow(shared,torch.randn(1,64,30),c,steps=1,guidance_scale=1.0)
        z2=sample_shortcut_flow(shared,torch.randn(1,64,30),c,steps=2,guidance_scale=1.0)
        assert z1.shape==z2.shape==(1,64,30)

    # Training-only Shortcut bootstrap works on the same architecture; no second consumer net.
    tiny=BalladFlowRenderer(latent_ch=64,d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.0,attention_impl='sdpa',shared_adaln=True,interval_conditioning=True,expert_fusion='joint',split_vibrato_validity=True)
    ema=BalladFlowRenderer(latent_ch=64,d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.0,attention_impl='sdpa',shared_adaln=True,interval_conditioning=True,expert_fusion='joint',split_vibrato_validity=True)
    ema.load_state_dict(tiny.state_dict(),strict=True); ema.eval().requires_grad_(False)
    zz=torch.randn(1,64,30); loss,met=shortcut_losses(tiny,ema,zz,controls(),4,.0); assert torch.isfinite(loss); loss.backward(); assert float(met['mean_h'])>0

    # Strict MIDI authority fix: CC3 is an authoritative runtime control while physical teacher labels can be unknown.
    assert shared.split_vibrato_validity
    assert float(c['vibrato_known'].min())==1.0 and float(c['vibrato_physics_known'].max())==0.0
    low={k:(v.clone() if hasattr(v,'clone') else v) for k,v in c.items()}; high={k:(v.clone() if hasattr(v,'clone') else v) for k,v in c.items()}
    low['vibrato'].zero_(); high['vibrato'].fill_(1.)
    xv=torch.randn(1,64,30)
    with torch.no_grad(): yl=shared(xv,t,flow_h=h,**low); yh=shared(xv,t,flow_h=h,**high)
    assert torch.isfinite(yl).all() and torch.isfinite(yh).all() and not torch.equal(yl,yh)

    # Shortcut checkpoints override legacy default step counts with their trained recommendation.
    fake=TorchFlowBackend(Path('.')); fake.models={'x':shared}; fake.model_meta={'x':{'sampling_family':'shortcut','supported_steps':[1,2,4,8],'recommended_steps':2}}
    assert fake._effective_steps(shared,8)==2

    # Q4 hidden physics: Manual identity; Assist creates role-dependent vibrato bloom without score edits.
    ev=[{'type':1,'part':i,'project_sample':0,'note':72-5*i} for i in range(4)]
    base=np.zeros(100,np.float32); on=np.zeros(100,np.float32); on[0]=1.; gate=np.ones(100,np.float32)
    b0,v0=coordinate_hidden_ensemble(base,base,gate,on,ev,0,0,48000,48000,0.0,fps=100)
    b1,v1=coordinate_hidden_ensemble(base,base,gate,on,ev,0,0,48000,48000,1.0,fps=100)
    b4,v4=coordinate_hidden_ensemble(base,base,gate,on,ev,3,0,48000,48000,1.0,fps=100)
    assert np.array_equal(b0,base) and np.array_equal(v0,base) and b1.max()>0 and not np.array_equal(v1,v4)

    # Persistent tile cache reuses byte-identical unaffected tiles.
    with tempfile.TemporaryDirectory() as td:
        cache=AudioTileCache(Path(td),max_mb=1); arr=np.linspace(-1,1,4096,dtype=np.float32)
        assert cache.get('a',len(arr)) is None; cache.put('a',arr); got=cache.get('a',len(arr)); assert got is not None and np.array_equal(got,arr)

    integrity_smoke()
    assert TorchFlowBackend._latent_shape(shared,10.0)==(64,300)
    print('v1.7 shared/tied/shortcut/authority/Q4/cache/integrity PASS')
    print('v16_frontier',old_p,'v17_shared',shared_p,'v17_tied',tied_p)
    print('shared reduction',f'{(1-shared_p/old_p)*100:.1f}%','tied reduction',f'{(1-tied_p/old_p)*100:.1f}%')
    print('decoder_only',dec_p,'shared+decoder FP16 MiB',f'{(shared_p+dec_p)*2/2**20:.2f}','tied+decoder FP16 MiB',f'{(tied_p+dec_p)*2/2**20:.2f}')

if __name__=='__main__': main()
