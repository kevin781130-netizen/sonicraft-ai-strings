from __future__ import annotations
import json,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from models.ballad_flow_renderer import BalladFlowRenderer
from models.vibrato_expert import VibratoControlExpert
from models.performance_experts import PerformanceExperts
from vibrato_calibration import VibratoCalibration
from performance_timing import TimingCalibration,target_transition

ROOT=Path(__file__).resolve().parents[1]
# neural/control smoke
B,T,C=2,36,1024
curve=lambda v: torch.full((B,T),float(v))
z=torch.randn(B,C,T);t=torch.rand(B);m=BalladFlowRenderer(latent_ch=C,d_model=64,layers=2,heads=4)
args=[curve(64),curve(1),curve(.05),curve(.7),curve(.6),curve(.5),curve(.9),curve(.7),curve(.5),curve(.5),curve(.5),curve(.38),curve(.5),curve(.5),curve(2),curve(-2),curve(.35),curve(.2),curve(68),curve(60/68),curve(2),curve(84),curve(2/3),curve(28),curve(5.3),curve(.03),curve(1),curve(1),curve(1),curve(1),curve(0),curve(1),curve(1)]
ins=torch.tensor([0,2]);art=torch.tensor([1,2]);player=torch.tensor([0,3]);art_curve=torch.cat([curve(1)[:1],curve(2)[:1]],0)
out=m(z,t,*args,ins,art,player,art_curve);out.square().mean().backward();assert torch.isfinite(out).all() and m.CONTROL_DIMS==34

# data-driven CC3 calibration is monotonic and instrument-specific capable
cal=VibratoCalibration({'all':[0,9,24,43,68],'0':[0,10,26,46,72]}, {'all':{'slow':4.5,'normal':5.4,'fast':6.4}}, {'all':{'early':130,'natural':245,'late':390}}, {'all':40})
assert cal.cc3_to_depth(0)==0 and cal.cc3_to_depth(32,0)<cal.cc3_to_depth(64,0)<cal.cc3_to_depth(96,0)<cal.cc3_to_depth(127,0)
assert 0<cal.depth_to_cc3(26,0)<1

# tempo scaling still works
pt=TimingCalibration.default();assert target_transition(56,'legato',.5,'normal',0,pt)['transition_ms']>target_transition(96,'legato',.5,'normal',0,pt)['transition_ms']

# synthetic real-audio analyzer smoke: 3s A4 with ~28-cent, 5.4Hz vibrato after a short straight onset.
with tempfile.TemporaryDirectory() as td:
    td=Path(td);sr=16000;dur=3.0;tt=np.arange(int(sr*dur))/sr
    depth=np.where(tt<.22,0.0,28.0); cents=depth*np.sin(2*np.pi*5.4*np.maximum(0,tt-.22));freq=440.0*(2.0**(cents/1200.0));phase=2*np.pi*np.cumsum(freq)/sr
    audio=(.22*np.sin(phase)).astype('float32');wav=td/'vib.wav';sf.write(wav,audio,sr)
    mf=td/'m.jsonl';mf.write_text(json.dumps({'dataset':'iowa_mis','audio':str(wav),'instrument':'violin','midi_note':69,'dynamic':'mf'})+'\n')
    od=td/'ana';idx=td/'idx.jsonl'
    cmd=[sys.executable,str(ROOT/'training/scripts/analyze_real_performance.py'),'--manifest',str(mf),'--out-dir',str(od),'--out-index',str(idx),'--registry',str(ROOT/'training/dataset_registry.json')]
    subprocess.check_call(cmd,cwd=ROOT)
    row=json.loads(idx.read_text().splitlines()[0]);d=np.load(row['file']);known=d['vibrato_depth_known']>.5
    assert known.sum()>30
    measured=float(np.median(d['vibrato_depth_cents'][known]));assert 7.0<=measured<=60.0,measured
    # rate/onset masks are independent from depth supervision.
    assert 'vibrato_rate_known' in d.files and 'vibrato_onset_known' in d.files
print('v0.8 smoke OK','renderer_params',sum(p.numel() for p in m.parameters()),'measured_synth_vib_cents',round(measured,2))
