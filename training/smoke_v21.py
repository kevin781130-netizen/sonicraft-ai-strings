from __future__ import annotations
import tempfile, json, math
from pathlib import Path
import numpy as np
import torch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from instrument_x_cleanroom import *
from polyphony import allocate_polyphonic_event_lanes
from stage_renderer import render_virtual_mics,mix_virtual_stage
from musicxml_import import convert_musicxml

# Flag decode / opt-in authority
flags=(2)| (5<<2) | (1<<5) | (1<<6) | (1<<7) | (4<<8) | (77<<11) | (2<<19) | (11<<21)
p=decode_flags(flags)
assert p.assist_level==2 and p.style==5 and p.smart_dynamics and p.smart_articulation and p.polyphony
assert p.retake_target==4 and p.retake_nonce==77 and p.stage_perspective==2 and abs(p.retake_amount-11/15)<1e-6
N=100
d=np.full(N,.6,np.float32);pitch=np.full(N,69,np.float32);gate=np.ones(N,np.float32);on=np.zeros(N,np.float32);on[0]=1
prog=np.linspace(0,1,N,dtype=np.float32);phr=prog.copy();pi=np.zeros(N,np.float32);ni=np.zeros(N,np.float32)
manual=PerformancePolicy(assist_level=0,smart_dynamics=True)
assert np.array_equal(predictive_dynamics(d,pitch,gate,on,prog,phr,pi,ni,68,manual),d)
auto=PerformancePolicy(assist_level=2,style=5,smart_dynamics=True,smart_articulation=True)
d2=predictive_dynamics(d,pitch,gate,on,prog,phr,pi,ni,68,auto);assert np.max(np.abs(d2-d))>1e-3
art=np.zeros(N,np.int64);dur=np.full(N,.22,np.float32);leg=np.zeros(N,np.float32)
a2=smart_articulation_curve(art,gate,on,dur,leg,pi,ni,132,auto);assert np.all(a2==6)
base={'dynamics':d.copy(),'attack_character':np.full(N,.4,np.float32),'short_tightness':np.full(N,.5,np.float32),'bow_change_prob':np.zeros(N,np.float32),'vibrato_onset':np.zeros(N,np.float32),'vibrato_jitter':np.zeros(N,np.float32)}
rp=PerformancePolicy(assist_level=2,retake_target=4,retake_nonce=9,retake_amount=.8)
r1=apply_targeted_retake(base,'abc',0,rp);r2=apply_targeted_retake(base,'abc',0,rp)
assert all(np.array_equal(r1[k],r2[k]) for k in r1)
r3=apply_targeted_retake(base,'abc',0,PerformancePolicy(assist_level=2,retake_target=4,retake_nonce=10,retake_amount=.8))
assert np.max(np.abs(r1['dynamics']-r3['dynamics']))>1e-5

# Independent polyphony: overlapping C4/E4/G4 produce three lanes and preserve note identity.
def ev(ps,t,n,part=0):return {'project_sample':ps,'type':t,'part':part,'note':n,'articulation':0,'velocity':.7,'tempo_bpm':120.,'controls':[.6,.5,.9,.86,.5,1,1,.18,.5,0,.5,.5,.38,0]}
events=[ev(0,1,60),ev(10,1,64),ev(20,1,67),ev(100,2,60),ev(110,2,64),ev(120,2,67)]
lanes=allocate_polyphonic_event_lanes(events,0,16);assert len(lanes)==3
notes=sorted([next(e['note'] for e in lane if e['type']==1) for lane in lanes]);assert notes==[60,64,67]

# Eleven virtual feeds and finite stereo stage.
x=torch.zeros(4800);x[0]=1
feeds=render_virtual_mics(x,48000,.3,2);assert len(feeds)==11
st=mix_virtual_stage(x,48000,.3,2);assert tuple(st.shape)==(4800,2) and torch.isfinite(st).all()
assert float(st.abs().sum())>0

# MusicXML import: chord + dynamic + articulation, dependency-free.
xml='''<?xml version="1.0"?><score-partwise version="3.1"><part-list><score-part id="P1"><part-name>Violin</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>4</divisions></attributes><direction><direction-type><dynamics><f/></dynamics></direction-type><sound tempo="120"/></direction><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><notations><articulations><staccato/></articulations></notations></note><note><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration></note></measure></part></score-partwise>'''
with tempfile.TemporaryDirectory() as td:
    fp=Path(td)/'x.musicxml';fp.write_text(xml)
    out=convert_musicxml(fp,48000,120)
    ons=[e for e in out['events'] if e['type']==1];assert len(ons)==2 and ons[0]['project_sample']==ons[1]['project_sample']==0
    assert ons[0]['articulation']==5 and abs(ons[0]['velocity']-.74)<1e-6

# CPU path must exist and no longer hard-fail on torch.cuda.is_available().
text=(ROOT/'runtime'/'model_backend.py').read_text()
assert "SONICRAFT_DEVICE" in text and "self.device='cuda' if" in text and "requested=='cuda' and not torch.cuda.is_available()" in text
print('v2.1 Instrument-X clean-room parity smoke PASS', {'lanes':len(lanes),'virtual_mics':len(feeds),'retake_delta':float(np.max(np.abs(r1['dynamics']-d)))})

# Full tiny CPU model-pack load/render: validates the no-GPU fallback mechanically.
import os, hashlib
from models.ballad_flow_renderer import BalladFlowRenderer
from models.string_vae64 import StringVAE64Decoder
from model_backend import TorchFlowBackend
from protocol import RequestHeader

def _sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    cfg={'d_model':32,'layers':1,'heads':4,'backbone':'adaln_dit','mlp_ratio':2.0,'dropout':0.0,'attention_impl':'sdpa'}
    m=BalladFlowRenderer(latent_ch=64,**cfg)
    torch.save({'model':m.state_dict(),'config':cfg,'latent_ch':64,'latent_hz':30.0,'codec_kind':'strings_vae64','codec_sample_rate':48000},td/'compact.pt')
    dec=StringVAE64Decoder(channels=4,latent_dim=64)
    torch.save({'decoder':dec.state_dict(),'config':{'channels':4,'latent_dim':64,'c_mults':(1,2,4,8,16),'strides':(2,4,5,5,8),'final_tanh':False},'codec_sample_rate':48000},td/'decoder.pt')
    (td/'prov.json').write_text('{}');(td/'metrics.json').write_text('{}')
    man={'schema':3,'product':'SONICRAFT AI Strings Q4','version':'2.1-cpu-smoke','commercial_safe':True,'release_approved':True,'profile':'standard','codec':{'kind':'strings_vae64','sample_rate':48000,'latent_ch':64,'latent_hz':30.0,'downsampling_ratio':1600},'files':[{'name':'compact.pt','role':'compact','sha256':_sha(td/'compact.pt')},{'name':'decoder.pt','role':'string_vae64','sha256':_sha(td/'decoder.pt')}],'provenance':{'file':'prov.json','sha256':_sha(td/'prov.json'),'contains_blocked_sources':False},'metrics':{'file':'metrics.json','sha256':_sha(td/'metrics.json')}}
    (td/'release_model_manifest.json').write_text(json.dumps(man))
    old=os.environ.get('SONICRAFT_DEVICE');os.environ['SONICRAFT_DEVICE']='cpu'
    try:
        b=TorchFlowBackend(td,steps=1,auto_steps=1,tile_seconds=2,tile_overlap=0)
        assert b.load(1),b.status()
        req=RequestHeader(1,1,0,3840,48000,2,1,1,120.0,.2,(1<<7))
        ce=[.6,.5,.9,.86,.5,1.,1.,.18,.5,0.,.5,.5,.38,0.]
        evs=[{'project_sample':0,'type':1,'part':0,'note':69,'articulation':0,'velocity':.7,'tempo_bpm':120.,'controls':ce},{'project_sample':3840,'type':2,'part':0,'note':69,'articulation':0,'velocity':0.,'tempo_bpm':120.,'controls':ce}]
        y=b.render(req,evs);assert y.shape==(3840,2) and np.isfinite(y).all()
        print('v2.1 CPU tiny-pack render PASS',b.status().name,y.shape)
    finally:
        if old is None:os.environ.pop('SONICRAFT_DEVICE',None)
        else:os.environ['SONICRAFT_DEVICE']=old
