#!/usr/bin/env python3
"""Export the compact SONICRAFT v1.8 frontier renderer/decoder to ONNX for ORT benchmarking.

Development-only bridge. The shipping runtime must not switch to ORT until numerical,
ABX, latency, VRAM and binary-size gates pass on the same trained checkpoints.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import torch
from torch import nn

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'training'))
from models.ballad_flow_renderer import BalladFlowRenderer
from models.string_vae64 import StringVAE64Decoder

RAW_NAMES=(
 'pitch','gate','onset','velocity','dynamics','vibrato','expression','legato','pitchbend',
 'transition_speed','short_tightness','attack_character','note_progress','phrase_position',
 'prev_interval','next_interval','bow_change_prob','vibrato_onset','tempo_bpm','seconds_per_beat',
 'note_duration_beats','transition_target_ms','speed_profile','vibrato_depth_cents','vibrato_rate_hz',
 'vibrato_jitter','dynamics_known','vibrato_known','expression_known','legato_known',
 'pitchbend_known','timing_known','articulation_known')

class PackedRenderer(nn.Module):
    def __init__(self, model): super().__init__(); self.model=model
    def forward(self, xt,t,flow_h,raw,vibrato_physics_known,frontier_context,instrument,articulation,player,articulation_curve):
        vals=[raw[...,i] for i in range(len(RAW_NAMES))]
        kw=dict(zip(RAW_NAMES,vals))
        return self.model(xt,t,instrument=instrument,articulation=articulation,player=player,
                          articulation_curve=articulation_curve,flow_h=flow_h,vibrato_physics_known=vibrato_physics_known,frontier_context=frontier_context,**kw)

class DecoderOnly(nn.Module):
    def __init__(self, dec): super().__init__(); self.dec=dec
    def forward(self,z): return self.dec(z)

def load_renderer(path):
    ck=torch.load(path,map_location='cpu'); cfg=dict(ck.get('config') or {})
    m=BalladFlowRenderer(latent_ch=int(ck.get('latent_ch',64)),**cfg).eval()
    m.load_state_dict(ck.get('ema',ck['model']),strict=True)
    return m,ck

def load_decoder(path):
    ck=torch.load(path,map_location='cpu'); cfg=dict(ck.get('config') or {})
    d=StringVAE64Decoder(channels=int(cfg.get('channels',16)),latent_dim=int(cfg.get('latent_dim',64)),
        c_mults=cfg.get('c_mults',(1,2,4,8,16)),strides=cfg.get('strides',(2,4,5,5,8)),
        final_tanh=bool(cfg.get('final_tanh',False))).eval()
    d.load_state_dict(ck['decoder'],strict=True); return d,ck

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--renderer',required=True); ap.add_argument('--decoder',required=True)
    ap.add_argument('--out-dir',default='build/ort_export'); ap.add_argument('--opset',type=int,default=18)
    a=ap.parse_args(); out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    m,rc=load_renderer(a.renderer); d,dc=load_decoder(a.decoder)
    ch=int(rc.get('latent_ch',64)); T=max(8,int(round(float(rc.get('latent_hz',30.0))*2.0)))
    xt=torch.randn(1,ch,T); t=torch.tensor([.5]); flow_h=torch.tensor([.25]); raw=torch.zeros(1,T,len(RAW_NAMES)); vib_phys=torch.zeros(1,T); context_dim=int(getattr(m,'frontier_context_dim',0) or 0); frontier_ctx=torch.zeros(1,max(1,context_dim),T)
    # Safe nominal controls make tracing representative without requiring a dataset row.
    defaults={'pitch':69.,'gate':1.,'velocity':.7,'dynamics':.65,'vibrato':.5,'expression':.9,'legato':1.,
              'pitchbend':.5,'transition_speed':.5,'short_tightness':.5,'attack_character':.38,
              'note_progress':.5,'phrase_position':.5,'tempo_bpm':68.,'seconds_per_beat':60/68,
              'note_duration_beats':2.,'dynamics_known':1.,'expression_known':1.,'legato_known':1.,
              'pitchbend_known':1.,'articulation_known':1.}
    for k,v in defaults.items(): raw[...,RAW_NAMES.index(k)]=v
    ids=torch.zeros(1,dtype=torch.long); art_curve=torch.ones(1,T)
    rw=PackedRenderer(m).eval(); dw=DecoderOnly(d).eval()
    rpath=out/'renderer_frontier.onnx'; dpath=out/'strings_vae64_decoder.onnx'
    torch.onnx.export(rw,(xt,t,flow_h,raw,vib_phys,frontier_ctx,ids,ids,ids,art_curve),rpath,opset_version=a.opset,
        input_names=['latent','flow_t','flow_h','controls','vibrato_physics_known','frontier_context','instrument','articulation','player','articulation_curve'],output_names=['velocity'],
        dynamic_axes={'latent':{0:'batch',2:'latent_time'},'flow_h':{0:'batch'},'controls':{0:'batch',1:'control_time'},'vibrato_physics_known':{0:'batch',1:'control_time'},'frontier_context':{0:'batch',2:'control_time'},'articulation_curve':{0:'batch',1:'control_time'},'velocity':{0:'batch',2:'latent_time'}})
    z=torch.randn(1,int(dc.get('latent_ch',64)),max(2,T));
    torch.onnx.export(dw,(z,),dpath,opset_version=a.opset,input_names=['latent'],output_names=['audio'],
        dynamic_axes={'latent':{0:'batch',2:'latent_time'},'audio':{0:'batch',2:'audio_time'}})
    meta={'schema':1,'renderer':str(rpath),'decoder':str(dpath),'raw_control_names':RAW_NAMES,
          'codec_kind':'strings_vae64','latent_ch':ch,'latent_hz':float(rc.get('latent_hz',30.0)),
          'codec_sample_rate':int(rc.get('codec_sample_rate',48000)),'frontier_context_dim':context_dim,
          'sampling_family':str(rc.get('sampling_family','rectified_flow')),'supported_steps':rc.get('supported_steps',[]),'recommended_steps':rc.get('recommended_steps'),
          'note':'Development benchmark only. Promote ORT only after PyTorch parity + ABX + latency/VRAM/size gates.'}
    (out/'export_manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print('ONNX export complete:',rpath,dpath)
    print('Next: convert this directory to ORT format to generate required_operators*.config.')
if __name__=='__main__': main()
