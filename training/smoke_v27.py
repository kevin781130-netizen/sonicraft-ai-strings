#!/usr/bin/env python3
from __future__ import annotations
import json,os,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'));sys.path.insert(0,str(ROOT/'training'))
from portable_rng_v27 import normal_array
from instrument_x_cleanroom import _smooth,PerformancePolicy,apply_targeted_retake
from control_builder_np import build_part_controls_np
from parity_trace_v27 import save_trace,first_divergence

def run(*cmd,**kw):return subprocess.run(cmd,check=True,text=True,capture_output=kw.pop('capture_output',False),**kw)

def rng_cpp_test(tmp):
 b=tmp/'build';run('cmake','-S',str(ROOT),'-B',str(b),'-DSONICRAFT_BUILD_VST3=OFF','-DSONICRAFT_BUILD_STANDALONE=OFF','-DSONICRAFT_BUILD_REALTIME_SIM=OFF','-DSONICRAFT_BUILD_LOW_LATENCY_SIM=OFF','-DSONICRAFT_BUILD_PRODUCT_SHELL=OFF','-DSONICRAFT_BUILD_ORT_INPROCESS_PROBE=OFF')
 run('cmake','--build',str(b),'--target','SonicraftParityRngSmokeV27','-j2')
 out=run(str(b/'SonicraftParityRngSmokeV27'),capture_output=True).stdout.strip().split(',')
 py=normal_array('SONICRAFT_V27_PARITY',12);bits=[f'{int(x):08x}' for x in py.view(np.uint32)]
 assert out==bits,(out,bits)
 return b

class Req:
 sample_rate=48000;start_sample=0;end_sample=9600;tempo_bpm=72.;flags=0

def ev(sample,typ,part,note,vel=.8):
 return {'project_sample':sample,'type':typ,'part':part,'note':note,'articulation':0,'velocity':vel,'controls':[.62,.5,.9,.86,.5,1,1,.18,.5,0,.5,.5,.38,0]}

def context_test():
 # lane contains only Vln I; full context contains a synchronized higher Vln II entry.
 lane=[ev(0,1,0,60),ev(9000,2,0,60)]
 all_events=lane+[ev(0,1,1,72),ev(9000,2,1,72)]
 c=build_part_controls_np(Req(),lane,0,context_events=all_events)
 # density / top-role context must see the other part; this was cut off in v2.6 ORT polyphony.
 assert float(np.max(c['frontier_context'][0,0]))>0.0
 assert float(np.max(c['frontier_context'][0,3]))<1.01

def retake_short_test():
 x=np.linspace(0,1,20,dtype=np.float32);assert len(_smooth(x,24))==20
 p=PerformancePolicy(retake_target=4,retake_nonce=7,retake_amount=.8)
 curves={'dynamics':x,'attack_character':x.copy(),'short_tightness':x.copy(),'bow_change_prob':x.copy(),'vibrato_onset':x.copy(),'vibrato_jitter':np.zeros_like(x)}
 a=apply_targeted_retake(curves,'backend-A',0,p);b=apply_targeted_retake(curves,'backend-B',0,p)
 for k in a: assert np.array_equal(a[k],b[k]),k
 assert all(len(np.asarray(v))==20 for v in a.values())

def debugger_test(tmp):
 arr={k:np.zeros((2,3),np.float32) for k in ('raw_controls','frontier_context','initial_latent','renderer_velocity','latent_after_step','final_latent','decoder_audio','stage_audio','final_mix')}
 ref=tmp/'ref.npz';nat=tmp/'nat.npz';save_trace(ref,'manual',arr)
 bad={k:v.copy() for k,v in arr.items()};bad['renderer_velocity'][1,2]=.01;save_trace(nat,'manual',bad)
 fd=first_divergence(np.load(ref),np.load(nat));assert fd and fd['stage']=='renderer_velocity' and fd['index']==[1,2]
 # CLI must fail closed on the same first divergence.
 cp=subprocess.run([sys.executable,str(ROOT/'training/scripts/compare_native_trace_v27.py'),'--reference',str(ref),'--native',str(nat),'--scenario','manual','--out',str(tmp/'diff.json')],capture_output=True,text=True)
 assert cp.returncode==3
 d=json.loads((tmp/'diff.json').read_text());assert d['first_divergence']['stage']=='renderer_velocity'

if __name__=='__main__':
 with tempfile.TemporaryDirectory(prefix='sonicraft_v27_') as td:
  tmp=Path(td);rng_cpp_test(tmp);context_test();retake_short_test();debugger_test(tmp)
 print('v2.7 Native Parity Forge smoke PASS: portable_rng_bit_exact, ensemble_context, short_retake, first_divergence')
