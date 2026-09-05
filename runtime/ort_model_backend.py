"""v2.2 no-PyTorch ONNX Runtime deployment challenger.

This module intentionally imports no torch. It is opt-in until the same trained v2.x checkpoint
passes numerical parity, codec/generated ABX, latency and <=160 MiB bundle gates.
"""
from __future__ import annotations
import hashlib,json,math,os
from pathlib import Path
import numpy as np
from control_builder_np import build_part_controls_np,midi_authority_base_np
from instrument_x_cleanroom import decode_flags
from polyphony import allocate_polyphonic_event_lanes
from stage_renderer_np import stage_bundle_np
from portable_rng_v27 import normal_array,event_seed_key

class BackendStatus:
    def __init__(self,ready,name,detail):self.ready=bool(ready);self.name=str(name);self.detail=str(detail)

class ORTFlowBackend:
    def __init__(self,model_dir:Path,steps=24,auto_steps=8,solver='euler',cfg_scale=1.0,auto_cfg_scale=1.0,**_):
        self.model_dir=Path(model_dir);self.ort_dir=Path(os.getenv('SONICRAFT_ORT_DIR','').strip() or (self.model_dir/'ORT'))
        self.steps=int(steps);self.auto_steps=int(auto_steps);self.solver=str(solver).lower();self.cfg_scale=float(cfg_scale);self.auto_cfg_scale=float(auto_cfg_scale)
        self.renderer=None;self.decoder=None;self._error='not loaded';self.backend_name='ort-unloaded';self.meta={};self.provider=''
    def _manifest(self):
        p=self.ort_dir/'export_manifest.json'
        if not p.is_file():raise FileNotFoundError(f'ORT export manifest missing: {p}')
        return json.loads(p.read_text(encoding='utf-8'))
    def _model_path(self,key,default):
        raw=str(self.meta.get(key,default));p=Path(raw)
        if not p.is_absolute():p=self.ort_dir/p.name
        if not p.is_file():
            # Prefer ORT format when conversion has been run; fall back to ONNX for validation.
            q=self.ort_dir/(Path(default).stem+'.ort')
            if q.is_file():p=q
        if not p.is_file():raise FileNotFoundError(f'{key} model missing: {p}')
        return p
    def fingerprint(self):
        try:
            h=hashlib.sha256()
            for p in (self.ort_dir/'export_manifest.json',self._model_path('renderer','renderer_frontier.onnx'),self._model_path('decoder','strings_vae64_decoder.onnx')):
                h.update(p.name.encode());h.update(hashlib.sha256(p.read_bytes()).digest())
            return h.hexdigest()
        except Exception:return 'ORT_UNVERIFIED'
    def status(self):return BackendStatus(self.renderer is not None and self.decoder is not None,self.backend_name,self._error or f'{self.provider}, no-PyTorch, 11-feed capable')
    def load(self,mode=1):
        try:
            import onnxruntime as ort
            self.meta=self._manifest();available=ort.get_available_providers();requested=os.getenv('SONICRAFT_DEVICE','auto').strip().lower()
            if requested=='cuda' and 'CUDAExecutionProvider' not in available:raise RuntimeError('SONICRAFT_DEVICE=cuda but ORT CUDAExecutionProvider is unavailable')
            providers=['CUDAExecutionProvider','CPUExecutionProvider'] if requested!='cpu' and 'CUDAExecutionProvider' in available else ['CPUExecutionProvider']
            so=ort.SessionOptions();so.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.renderer=ort.InferenceSession(str(self._model_path('renderer','renderer_frontier.onnx')),sess_options=so,providers=providers)
            self.decoder=ort.InferenceSession(str(self._model_path('decoder','strings_vae64_decoder.onnx')),sess_options=so,providers=providers)
            self.provider=self.renderer.get_providers()[0];self.backend_name='ort-cuda' if 'CUDA' in self.provider else 'ort-cpu';self._error='';return True
        except Exception as e:self.renderer=None;self.decoder=None;self._error=f'{type(e).__name__}: {e}';return False
    def _effective_steps(self,requested):
        if str(self.meta.get('sampling_family','rectified_flow')).lower()!='shortcut':return max(1,int(requested))
        sup=sorted(set(int(x) for x in self.meta.get('supported_steps',[]) if int(x)>0));rec=int(self.meta.get('recommended_steps',0) or requested)
        return min(sup,key=lambda x:(abs(x-rec),x)) if sup else max(1,rec)
    def _run_velocity(self,x,t,h,c,guidance):
        def inp(cc):return {'latent':x.astype(np.float32,copy=False),'flow_t':t,'flow_h':h,'controls':cc['raw'],'vibrato_physics_known':cc['vibrato_physics_known'],
                            'frontier_context':cc['frontier_context'],'instrument':cc['instrument'],'articulation':cc['articulation'],'player':cc['player'],'articulation_curve':cc['articulation_curve']}
        full=self.renderer.run(None,inp(c))[0].astype(np.float32,copy=False)
        if guidance<=1.000001:return full
        base=midi_authority_base_np(c);b=self.renderer.run(None,inp(base))[0].astype(np.float32,copy=False)
        return b+(full-b)*float(guidance)
    def _render_voice(self,req,c,steps,guidance,seed):
        frames=max(1,int(req.end_sample-req.start_sample));dur=frames/float(req.sample_rate);ch=int(self.meta.get('latent_ch',64));hz=float(self.meta.get('latent_hz',30.));tlat=max(2,int(math.ceil(dur*hz)))
        # `seed` may be a portable textual key in v2.7; legacy integer seeds still work.
        key=str(seed) if isinstance(seed,str) else f'legacy-seed|{int(seed)}'
        x=normal_array(key,ch*tlat).reshape(1,ch,tlat);dt=1./max(1,steps)
        for i in range(max(1,steps)):
            t=np.asarray([i/max(1,steps)],np.float32);h=np.asarray([dt],np.float32);v0=self._run_velocity(x,t,h,c,guidance)
            if self.solver=='heun' and i<steps-1:
                xp=x+v0*dt;t1=np.asarray([(i+1)/steps],np.float32);v1=self._run_velocity(xp,t1,h,c,guidance);x=x+(v0+v1)*(.5*dt)
            else:x=x+v0*dt
        y=np.asarray(self.decoder.run(None,{'latent':x.astype(np.float32,copy=False)})[0],np.float32).reshape(-1)
        codec_sr=int(self.meta.get('codec_sample_rate',48000));target=frames
        if len(y)!=target or codec_sr!=int(req.sample_rate):
            host_len=max(1,int(round(len(y)*int(req.sample_rate)/max(1,codec_sr))));old=np.linspace(0,1,len(y),endpoint=False);new=np.linspace(0,1,host_len,endpoint=False);y=np.interp(new,old,y).astype(np.float32)
        if len(y)<target:y=np.pad(y,(0,target-len(y)))
        return y[:target].astype(np.float32)
    def _seed(self,req,events,part,voice):
        # Backend/model fingerprint must not change the performed take.
        return event_seed_key(req.start_sample,req.end_sample,req.sample_rate,part,voice,events)
    @staticmethod
    def _room_amount(events,part):
        v=[float(e['controls'][7]) for e in events if int(e.get('part',-1))==part and e.get('controls') and len(e['controls'])>7]
        return float(np.clip(np.median(v) if v else .18,0,1))
    def render(self,req,events):
        if self.renderer is None or self.decoder is None:
            if not self.load(req.mode):raise RuntimeError(self._error)
        pol=decode_flags(int(req.flags));channels=34 if pol.multi_out else 2;frames=max(1,int(req.end_sample-req.start_sample));mix=np.zeros((frames,channels),np.float32)
        steps=self._effective_steps(self.auto_steps if int(req.mode)==1 else self.steps);guidance=self.auto_cfg_scale if int(req.mode)==1 else self.cfg_scale
        for part in range(min(4,int(req.part_count))):
            lanes=allocate_polyphonic_event_lanes(events,part,max_voices=16) if pol.polyphony else [[e for e in events if int(e.get('part',-1))==part or int(e.get('type',0))==5]]
            for voice,lane in enumerate(lanes):
                c=build_part_controls_np(req,lane,part,self.fingerprint(),context_events=events)
                if float(np.max(c['gate']))<=0:continue
                y=self._render_voice(req,c,steps,guidance,self._seed(req,lane,part,voice))/max(1.,math.sqrt(len(lanes)))
                stage=stage_bundle_np(y,int(req.sample_rate),self._room_amount(lane,part),pol.stage_perspective)
                base=[-.45,-.15,.12,.38][part];spread=(voice-(len(lanes)-1)*.5)*.055;pan=float(np.clip(base+spread,-.92,.92));gl=math.sqrt(.5*(1-pan));gr=math.sqrt(.5*(1+pan))
                pairs=17 if pol.multi_out else 1
                for j in range(pairs):mix[:,2*j]+=stage[:,2*j]*gl;mix[:,2*j+1]+=stage[:,2*j+1]*gr
        return np.clip(mix,-.98,.98).astype(np.float32)
