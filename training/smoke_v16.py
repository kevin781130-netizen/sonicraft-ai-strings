from __future__ import annotations
import json, hashlib, sys, tempfile
from pathlib import Path
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from models.ballad_flow_renderer import BalladFlowRenderer
from models.string_vae64 import StringVAE64
from flow_sampler import sample_rectified_flow, midi_authority_base
from model_backend import TorchFlowBackend
from release_integrity import verify_release_manifest
from quartet_interaction import coordinate_hidden_bow


def controls(B=1,N=30,dev='cpu'):
    f=lambda v: torch.full((B,N),float(v),device=dev)
    return dict(pitch=f(69),gate=f(1),onset=f(0),velocity=f(.7),dynamics=f(.65),vibrato=f(.5),expression=f(.9),legato=f(1),pitchbend=f(.5),
        transition_speed=f(.5),short_tightness=f(.5),attack_character=f(.38),note_progress=f(.5),phrase_position=f(.5),prev_interval=f(0),next_interval=f(2),
        bow_change_prob=f(.2),vibrato_onset=f(.3),tempo_bpm=f(68),seconds_per_beat=f(60/68),note_duration_beats=f(2),transition_target_ms=f(80),speed_profile=f(0),
        vibrato_depth_cents=f(25),vibrato_rate_hz=f(5.2),vibrato_jitter=f(.03),dynamics_known=f(1),vibrato_known=f(1),expression_known=f(1),legato_known=f(1),pitchbend_known=f(1),timing_known=f(1),articulation_known=f(1),
        instrument=torch.zeros(B,dtype=torch.long,device=dev),articulation=torch.ones(B,dtype=torch.long,device=dev),player=torch.zeros(B,dtype=torch.long,device=dev),articulation_curve=f(1))


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def integrity_smoke():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for n in ('frontier.pt','hq.pt','decoder.pt','training_provenance.json','release_metrics.json'):
            (td/n).write_bytes(b'v16-'+n.encode())
        m={'schema':3,'product':'SONICRAFT AI Strings Q4','version':'1.6.0-frontier','commercial_safe':True,'release_approved':True,'profile':'full_hq',
           'codec':{'kind':'strings_vae64','sample_rate':48000,'latent_ch':64,'latent_hz':30.0,'downsampling_ratio':1600},
           'files':[{'name':'frontier.pt','role':'compact','sha256':sha(td/'frontier.pt')},{'name':'hq.pt','role':'hq','sha256':sha(td/'hq.pt')},{'name':'decoder.pt','role':'string_vae64','sha256':sha(td/'decoder.pt')}],
           'provenance':{'file':'training_provenance.json','sha256':sha(td/'training_provenance.json'),'contains_blocked_sources':False},
           'metrics':{'file':'release_metrics.json','sha256':sha(td/'release_metrics.json')}}
        (td/'release_model_manifest.json').write_text(json.dumps(m),encoding='utf-8')
        got=verify_release_manifest(td); assert got['verified'] and got['manifest']['_capabilities']['codec']=='strings_vae64'


def main():
    torch.manual_seed(16)
    # 48 kHz / 1600x / 64-d geometry, with a tiny release decoder.
    vae=StringVAE64(channels=16)
    wav=torch.randn(1,1,3200,requires_grad=True); rec,mu,lv=vae(wav,sample=False)
    assert mu.shape==(1,64,2) and rec.shape==wav.shape and torch.isfinite(rec).all()
    (rec.square().mean()+1e-5*(mu.square()+lv.square()).mean()).backward()
    vae_p=sum(p.numel() for p in vae.parameters()); dec_p=sum(p.numel() for p in vae.decoder.parameters())
    print('VAE64 forward/backward PASS','total',vae_p,'decoder_only',dec_p,'latent',tuple(mu.shape))

    # v1.4 legacy and v1.5 DiT state-dict paths remain loadable.
    legacy=BalladFlowRenderer(d_model=64,layers=2,heads=4)
    legacy2=BalladFlowRenderer(d_model=64,layers=2,heads=4); legacy2.load_state_dict(legacy.state_dict(),strict=True)
    dit15=BalladFlowRenderer(d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0)
    dit15b=BalladFlowRenderer(d_model=64,layers=2,heads=4,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0,attention_impl='mha'); dit15b.load_state_dict(dit15.state_dict(),strict=True)

    c=controls(); x=torch.randn(1,64,30,requires_grad=True); t=torch.rand(1)
    frontier=BalladFlowRenderer(latent_ch=64,d_model=192,layers=6,heads=8,backbone='adaln_dit',mlp_ratio=2.0,dropout=0.0,attention_impl='sdpa')
    frontier.latent_hz=30.0
    y=frontier(x,t,**c); assert y.shape==x.shape and torch.isfinite(y).all(); y.square().mean().backward()
    with torch.no_grad():
        z=sample_rectified_flow(frontier,torch.randn(1,64,30),c,steps=2,solver='euler',guidance_scale=1.1)
        assert z.shape==(1,64,30); base=midi_authority_base(c); assert float(base['dynamics'].abs().max())==0.0 and float(base['pitch'].mean())==69.0
    assert TorchFlowBackend._latent_shape(frontier,10.0)==(64,300)

    # Zero-weight Q4 coordinator: Manual is bit-identical; Assist/Auto can strengthen
    # hidden ensemble re-bow intent at coincident entries without touching score authority.
    ev=[{'type':1,'part':0,'project_sample':0,'note':72},{'type':2,'part':0,'project_sample':48000,'note':72},
        {'type':1,'part':1,'project_sample':0,'note':67},{'type':2,'part':1,'project_sample':48000,'note':67},
        {'type':1,'part':2,'project_sample':0,'note':60},{'type':2,'part':2,'project_sample':48000,'note':60}]
    base=torch.zeros(100).numpy(); on=base.copy(); on[0]=1.0
    manual=coordinate_hidden_bow(base,on,ev,1,0,48000,48000,0.0); assist=coordinate_hidden_bow(base,on,ev,1,0,48000,48000,1.0)
    assert (manual==base).all() and float(assist.max())>0.0

    nano15=BalladFlowRenderer(latent_ch=1024,d_model=256,layers=8,heads=8,backbone='adaln_dit',mlp_ratio=2.5,dropout=0.0)
    np_=sum(p.numel() for p in nano15.parameters()); fp=sum(p.numel() for p in frontier.parameters()); assert fp<np_
    integrity_smoke()
    print('SDPA/CFG/geometry/legacy/integrity PASS','v15_nano',np_,'v16_frontier',fp,'renderer_reduction',f'{(1-fp/np_)*100:.1f}%')
    print('theoretical FP16 core MiB',f'{(fp+dec_p)*2/2**20:.2f}','(frontier renderer + width16 decoder only; excludes framework/runtime)')

if __name__=='__main__': main()
