from __future__ import annotations
import json, os, subprocess, sys, tempfile, hashlib
from pathlib import Path
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from instrument_x_cleanroom import decode_flags
from stage_renderer_np import stage_bundle_np, MIC_NAMES
from control_builder_np import build_part_controls_np
from protocol import RequestHeader,TYPE_RENDER

# 1) 25th bit requests true DAW multi-out without changing existing policy defaults.
p=decode_flags(1<<25)
assert p.multi_out is True
assert decode_flags(0).multi_out is False

# 2) Pure NumPy controls + 24ch (master + eleven stereo feed) stage.
sr=48000
req=RequestHeader(TYPE_RENDER,22,0,12000,sr,2,4,1,72.0,.25,1<<25)
ctrl=[.66,.42,.91,.84,.5,1.,1.,.2,.5,0.,.5,.5,.38,0.]
events=[
 {'project_sample':0,'type':1,'part':0,'note':69,'articulation':0,'velocity':.78,'tempo_bpm':72.,'controls':ctrl},
 {'project_sample':11900,'type':2,'part':0,'note':69,'articulation':0,'velocity':0.,'tempo_bpm':72.,'controls':ctrl},
]
c=build_part_controls_np(req,events,0,'smoke-v22')
assert c['raw'].shape[0]==1 and c['raw'].shape[2]==33
x=np.zeros(2400,np.float32);x[0]=.1
stage=stage_bundle_np(x,sr,.25,1)
assert stage.shape==(2400,24) and np.isfinite(stage).all() and np.max(np.abs(stage[:,2:]))>0

# 3) Build a directional room profile only from synthetic/user-owned stand-in IRs.
with tempfile.TemporaryDirectory() as td:
    td=Path(td); ir=td/'ir';ir.mkdir(); profile=td/'room.json'
    for i,name in enumerate(MIC_NAMES):
        y=np.zeros((256,2),np.float32); y[4+i,0]=1.; y[5+i,1]=.8
        sf.write(ir/f'{name}.wav',y,sr,subtype='PCM_24')
    subprocess.run([sys.executable,str(ROOT/'training/scripts/build_room_profile_v22.py'),'--ir-dir',str(ir),'--out',str(profile),'--taps','64'],check=True,stdout=subprocess.DEVNULL)
    rp=json.loads(profile.read_text())
    assert len(rp['feeds'])==11 and len(rp['sources'])==11 and rp['ownership_required'] is True
    old=os.environ.get('SONICRAFT_ROOM_PROFILE');os.environ['SONICRAFT_ROOM_PROFILE']=str(profile)
    try:
        calibrated=stage_bundle_np(x,sr,.25,1)
        assert calibrated.shape==(2400,24) and np.isfinite(calibrated).all()
    finally:
        if old is None:os.environ.pop('SONICRAFT_ROOM_PROFILE',None)
        else:os.environ['SONICRAFT_ROOM_PROFILE']=old

# 4) The ORT wiring smoke uses fake inference sessions; real ONNX parity is a separate promotion gate.
subprocess.run([sys.executable,str(ROOT/'runtime/smoke_ort_backend_v22.py')],check=True,stdout=subprocess.DEVNULL)

# 5) Prove runtime modules can import while every torch import is actively blocked.
code=f'''\nimport builtins,sys\norig=builtins.__import__\ndef guard(name,*a,**k):\n    if name=="torch" or name.startswith("torch."): raise ImportError("torch intentionally blocked")\n    return orig(name,*a,**k)\nbuiltins.__import__=guard\nsys.path.insert(0,{str(ROOT/'runtime')!r})\nimport model_backend,ort_model_backend,control_builder_np,stage_renderer_np,renderer_service\nprint("PASS")\n'''
r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
assert r.returncode==0 and 'PASS' in r.stdout,(r.stdout,r.stderr)

# 6) Footprint evidence hashes every artifact, and native-runtime promotion is fail-closed.
with tempfile.TemporaryDirectory() as td:
    td=Path(td); bundle=td/'bundle';bundle.mkdir();(bundle/'Models').mkdir()
    # tiny stand-ins are enough to test policy mechanics, not claimed production runtime size.
    (bundle/'onnxruntime.dll').write_bytes(b'ORT-v22')
    (bundle/'Models'/'renderer_frontier.ort').write_bytes(b'renderer')
    (bundle/'Models'/'strings_vae64_decoder.ort').write_bytes(b'decoder')
    fp=td/'footprint.json'
    subprocess.run([sys.executable,str(ROOT/'training/scripts/verify_native_runtime_bundle_v22.py'),'--bundle',str(bundle),'--out',str(fp),'--require-models'],check=True,stdout=subprocess.DEVNULL)
    f=json.loads(fp.read_text());assert f['schema']==2 and f['passed'] and len(f['artifacts'])==3
    assert all(len(a['sha256'])==64 for a in f['artifacts'])
    numerical=td/'numerical.json'; nd={'schema':1,'passed':True,'pair_count':3};nd['evidence_id']=hashlib.sha256(json.dumps(nd,sort_keys=True,separators=(',',':')).encode()).hexdigest();numerical.write_text(json.dumps(nd))
    abx=td/'abx.json'; abx.write_text(json.dumps({'schema':2,'transparency_pass':True,'listener_count':5,'trial_count':100,'accuracy':.49,'significant_above_chance':False}))
    acoustic=td/'acoustic.json'; acoustic.write_text(json.dumps({'promotion_pass':True,'promotion_id':'a'*64}))
    out=td/'promotion.json'
    subprocess.run([sys.executable,str(ROOT/'training/scripts/build_native_runtime_promotion_v22.py'),'--footprint',str(fp),'--numerical',str(numerical),'--runtime-abx',str(abx),'--acoustic-promotion',str(acoustic),'--out',str(out)],check=True,stdout=subprocess.DEVNULL)
    pr=json.loads(out.read_text());assert pr['promotion_pass'] and len(pr['runtime_promotion_id'])==64
    # Tamper the policy report to exceed 160 MiB: promotion must fail.
    bad=dict(f);bad['mib']=161.;bad.pop('evidence_id',None);bad['evidence_id']=hashlib.sha256(json.dumps(bad,sort_keys=True,separators=(',',':')).encode()).hexdigest();badp=td/'badfp.json';badp.write_text(json.dumps(bad))
    rr=subprocess.run([sys.executable,str(ROOT/'training/scripts/build_native_runtime_promotion_v22.py'),'--footprint',str(badp),'--numerical',str(numerical),'--runtime-abx',str(abx),'--acoustic-promotion',str(acoustic),'--out',str(td/'bad.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    assert rr.returncode!=0
    # Replace a model after footprint verification while retaining the original report: promotion must fail.
    (bundle/'Models'/'renderer_frontier.ort').write_bytes(b'REPLACED')
    rr=subprocess.run([sys.executable,str(ROOT/'training/scripts/build_native_runtime_promotion_v22.py'),'--footprint',str(fp),'--numerical',str(numerical),'--runtime-abx',str(abx),'--acoustic-promotion',str(acoustic),'--out',str(td/'tampered.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    assert rr.returncode!=0

# 7) Static VST contract: 12 stereo buses, bit25 request, and 24ch shadow-cache path.
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
shadow=(ROOT/'src/shadow_render_client.cpp').read_text(encoding='utf-8')
assert proc.count('addAudioOutput')>=12
for name in ('Q4 Master','Spot L','Spot C','Spot R','Tree L','Tree C','Tree R','Wide L','Wide R','Room L','Room R','Rear'):
    assert name in proc
assert '<<25' in shadow and 'multiOut' in shadow
assert 'channels==24' in shadow or 'channels!=24' in shadow

print('v2.2 Platform Kill Gap smoke PASS',{
    'vst_output_buses':12,'wire_channels':24,'virtual_feeds':11,'raw_controls':33,
    'native_core':'no-torch-capable','consumer_neural_params_added':0})
