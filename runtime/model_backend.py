from __future__ import annotations
import math, os, sys, json, hashlib
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from release_integrity import verify_release_manifest, IntegrityError
from flow_sampler import sample_rectified_flow
from quartet_interaction import coordinate_hidden_bow, coordinate_hidden_ensemble
from frontier_context import frontier_context_curves
from tile_cache import AudioTileCache
from instrument_x_cleanroom import decode_flags, predictive_dynamics, smart_articulation_curve, apply_targeted_retake, articulation_stack_modifiers, phrase_director_curve
from string_physical_runtime_v42 import physical_curves,apply_string_physical_residuals
from string_ensemble_runtime_v44 import apply_ensemble_event_timing_v44
from string_gesture_runtime_v45 import smooth_voice_controls_v45,smooth_physical_curves_v45
from string_transition_runtime_v46 import apply_continuous_transition_paths_v46
from string_phrase_runtime_v47 import apply_phrase_longline_v47
from polyphony import allocate_polyphonic_event_lanes
from stage_renderer import mix_virtual_stage, render_stage_bundle

RUNTIME_DIR = Path(__file__).resolve().parent
ROOT = RUNTIME_DIR.parents[0]
TRAIN = ROOT / 'training'
# Source tree: training/models. Installed runtime: Runtime/models. Keep inference code tiny and self-contained.
for candidate in (RUNTIME_DIR, TRAIN):
    if str(candidate) not in sys.path: sys.path.insert(0, str(candidate))

@dataclass
class BackendStatus:
    ready: bool
    name: str
    detail: str

class MockBackend:
    """Engineering-only renderer used to validate IPC/crossfade. Never a release model."""
    def status(self): return BackendStatus(True, 'mock', 'engineering smoke renderer')
    def _effective_steps(self, model, requested):
        key=next((k for k,v in self.models.items() if v is model),None)
        meta=self.model_meta.get(key,{}) if key else {}
        if str(meta.get('sampling_family','rectified_flow')).lower()!='shortcut': return max(1,int(requested))
        supported=sorted(set(int(x) for x in (meta.get('supported_steps') or []) if int(x)>0))
        rec=int(meta.get('recommended_steps',0) or 0)
        desired=rec if rec>0 else max(1,int(requested))
        if not supported: return desired
        return min(supported,key=lambda x:(abs(x-desired),x))

    def render(self, req, events):
        sr = int(req.sample_rate)
        frames = max(1, int(req.end_sample - req.start_sample))
        t = np.arange(frames, dtype=np.float32) / sr
        audio = np.zeros((frames,2), np.float32)
        # Render observed notes as quiet sine tones. This is deliberately obvious/non-HQ.
        active = {}
        sorted_events = sorted(events, key=lambda e: e['project_sample'])
        boundaries = [req.start_sample] + [max(req.start_sample,min(req.end_sample,e['project_sample'])) for e in sorted_events] + [req.end_sample]
        by_sample = {}
        for e in sorted_events: by_sample.setdefault(e['project_sample'], []).append(e)
        pos = req.start_sample
        phase = {}
        for nxt in boundaries[1:]:
            if nxt > pos and active:
                a = pos - req.start_sample; b = nxt - req.start_sample
                tt = np.arange(b-a, dtype=np.float32) / sr
                seg = np.zeros(b-a, np.float32)
                for key,(note,vel,part) in list(active.items()):
                    f = 440.0 * (2.0 ** ((note-69)/12.0))
                    p0 = phase.get(key, 0.0)
                    ph = p0 + 2*np.pi*f*tt
                    seg += (0.03*vel*np.sin(ph)).astype(np.float32)
                    phase[key] = float((p0 + 2*np.pi*f*((b-a)/sr))%(2*np.pi))
                audio[a:b,0] += seg*0.96; audio[a:b,1] += seg
            for e in by_sample.get(nxt,[]):
                key=(e['part'],int(e.get('voice_lane',-1)),e['note'])
                if e['type']==1: active[key]=(e['note'],e['velocity'],e['part'])
                elif e['type']==2: active.pop(key,None)
            pos=nxt
        fade=max(1,min(int(sr*.015),frames//4))
        if fade>1:
            g=np.linspace(0,1,fade,dtype=np.float32); audio[:fade]*=g[:,None]; audio[-fade:]*=g[::-1,None]
        if decode_flags(int(req.flags)).multi_out:
            # Engineering-only 34ch shape: master + 16 stereo aux clones with deterministic gains.
            # The production Torch backend renders physically distinct virtual feeds.
            aux=[audio]
            for i in range(16): aux.append(audio*(0.30+0.02*i))
            return np.concatenate(aux,axis=1).astype(np.float32)
        return audio

class TorchFlowBackend:
    """Actual local CUDA path: rectified-flow renderer -> Descript DAC decoder.

    It becomes ready only when BOTH renderer and fine-tuned decoder checkpoints exist.
    No silent fallback is used in release mode; if weights are missing the VST keeps LIVE preview.
    """
    def __init__(self, model_dir: Path, steps=24, auto_steps=8, solver='euler', cfg_scale=1.0, auto_cfg_scale=1.0, tile_seconds=10.0, tile_overlap=1.0, tile_cache_dir=None, tile_cache_mb=768.0):
        self.model_dir=Path(model_dir); self.steps=int(steps); self.auto_steps=int(auto_steps); self._error='not loaded'
        self.solver=str(solver).lower(); self.cfg_scale=float(cfg_scale); self.auto_cfg_scale=float(auto_cfg_scale)
        self.tile_seconds=max(2.0,float(tile_seconds)); self.tile_overlap=max(0.0,min(float(tile_overlap),self.tile_seconds*0.45))
        self.torch=None; self.dac=None; self.decoder=None; self.decoder_kind=None; self.codec_sample_rate=44100
        self.device='cpu'; self.backend_name='torch-local'; self.models={}; self.model_paths={}; self.model_meta={}; self.integrity=None
        self.allow_unverified=os.getenv('SONICRAFT_ALLOW_UNVERIFIED_MODELS','').strip()=='1'
        self.tile_cache=AudioTileCache(tile_cache_dir,max_mb=tile_cache_mb)
        self.tile_cache_hits=0; self.tile_cache_misses=0
    def _file_for_role(self, role):
        if not self._verify_integrity(): return None
        m=(self.integrity or {}).get('manifest') or {}
        for f in m.get('files',[]):
            if f.get('role')==role:
                p=self.model_dir/f.get('name','')
                if p.is_file(): return p
        return None
    def _decoder_path(self, codec_kind=None):
        kind=str(codec_kind or self.decoder_kind or self._manifest_codec_kind()).lower()
        return self._file_for_role('string_vae64') if kind=='strings_vae64' else self._file_for_role('dac')
    def _manifest_codec_kind(self):
        if not self._verify_integrity(): return 'dac44'
        m=(self.integrity or {}).get('manifest') or {}
        return str((m.get('codec') or {}).get('kind','dac44')).lower()
    def _dac_base_path(self):
        return self._file_for_role('dac_base')
    def _renderer_path(self, mode=2):
        if int(mode)==1:
            return self._file_for_role('compact') or self._file_for_role('hq')
        return self._file_for_role('hq')
    def fingerprint(self):
        if not self._verify_integrity(): return 'UNVERIFIED'
        m=(self.integrity or {}).get('manifest') or {}
        parts=[str(m.get('version',''))]
        for f in sorted(m.get('files',[]),key=lambda x:(x.get('role',''),x.get('name',''))): parts.append(str(f.get('sha256','')))
        # Inference settings affect the waveform and therefore must invalidate the phrase cache.
        parts += [f'steps={self.steps}',f'auto={self.auto_steps}',f'solver={self.solver}',
                  f'cfg={self.cfg_scale:.4f}',f'autocfg={self.auto_cfg_scale:.4f}',
                  f'tile={self.tile_seconds:.3f}',f'overlap={self.tile_overlap:.3f}']
        return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()
    def _verify_integrity(self):
        if self.integrity is not None: return bool(self.integrity.get('verified') or self.integrity.get('dev_override'))
        try:
            self.integrity=verify_release_manifest(self.model_dir, allow_dev=self.allow_unverified)
            return bool(self.integrity.get('verified') or self.integrity.get('dev_override'))
        except IntegrityError as e:
            self._error=f'model integrity: {e}'; return False

    def status(self):
        if not self._verify_integrity(): return BackendStatus(False,self.backend_name,self._error)
        r=self._renderer_path(2) or self._renderer_path(1); d=self._decoder_path(self._manifest_codec_kind())
        if self.decoder is not None and self.models:
            caps=((self.integrity or {}).get('manifest') or {}).get('_capabilities',{})
            hq='HQ ready' if caps.get('hq') else 'HQ unavailable (Standard profile)'
            return BackendStatus(True,self.backend_name,f'{self.device}, {self.decoder_kind}, predictive performance director, independent polyphony, virtual 11-mic stage, Q4 hidden physics, tile cache {self.tile_cache_hits}/{self.tile_cache_misses}, AUTO {self.auto_steps} steps, {self.solver}, tile {self.tile_seconds:g}s, {hq}')
        if self._error!='not loaded': return BackendStatus(False,self.backend_name,self._error)
        if r and d: return BackendStatus(False,self.backend_name,'weights present; local model has not been loaded yet')
        return BackendStatus(False,self.backend_name,'missing renderer/decoder checkpoints in Models')
    def _load_decoder(self, torch, codec_kind, codec_sample_rate):
        kind=str(codec_kind).lower()
        if self.decoder is not None:
            if self.decoder_kind!=kind:
                self._error=f'mixed codec kinds in one model pack: {self.decoder_kind} vs {kind}'; return False
            return True
        dpath=self._decoder_path(kind)
        if kind=='strings_vae64':
            if not dpath: self._error='missing manifest-approved strings VAE64 decoder checkpoint'; return False
            from models.string_vae64 import StringVAE64Decoder
            dck=torch.load(dpath,map_location='cpu'); cfg=dict(dck.get('config') or {})
            dec=StringVAE64Decoder(channels=int(cfg.get('channels',16)),latent_dim=int(cfg.get('latent_dim',64)),
                c_mults=cfg.get('c_mults',(1,2,4,8,16)),strides=cfg.get('strides',(2,4,5,5,8)),
                final_tanh=bool(cfg.get('final_tanh',False))).to(self.device).eval()
            dec.load_state_dict(dck['decoder'],strict=True); self.decoder=dec; self.dac=None
            self.decoder_kind=kind; self.codec_sample_rate=int(codec_sample_rate or dck.get('codec_sample_rate',48000)); return True
        if not dpath: self._error='missing fine-tuned DAC decoder checkpoint'; return False
        import dac
        base=self._dac_base_path()
        if not base: self._error='missing manifest-approved Descript DAC 44.1k/16kbps base weight'; return False
        dm=dac.DAC.load(base).to(self.device).eval(); dck=torch.load(dpath,map_location='cpu'); dm.decoder.load_state_dict(dck['decoder'],strict=True)
        self.dac=dm; self.decoder=dm; self.decoder_kind='dac44'; self.codec_sample_rate=44100; return True
    def load(self, mode=2):
        if not self._verify_integrity(): return False
        try:
            import torch
            from models.ballad_flow_renderer import BalladFlowRenderer
            requested=os.getenv('SONICRAFT_DEVICE','auto').strip().lower()
            if requested not in ('auto','cuda','cpu'): requested='auto'
            if requested=='cuda' and not torch.cuda.is_available(): self._error='SONICRAFT_DEVICE=cuda but CUDA is not available'; return False
            self.device='cuda' if (requested!='cpu' and torch.cuda.is_available()) else 'cpu'
            self.backend_name='torch-cuda' if self.device=='cuda' else 'torch-cpu'
            self.torch=torch; torch.set_float32_matmul_precision('high')
            rpath=self._renderer_path(mode)
            if not rpath: self._error='missing renderer checkpoint in Models'; return False
            key=str(rpath.resolve())
            if key not in self.models:
                ck=torch.load(rpath,map_location='cpu'); cfg=dict(ck.get('config') or ({'d_model':384,'layers':8,'heads':8} if 'compact' in rpath.name.lower() else {'d_model':512,'layers':10,'heads':8}))
                latent_ch=int(ck.get('latent_ch',1024)); codec_kind=str(ck.get('codec_kind',self._manifest_codec_kind())).lower()
                latent_hz=float(ck.get('latent_hz',30.0 if codec_kind=='strings_vae64' else 25.0)); codec_sr=int(ck.get('codec_sample_rate',48000 if codec_kind=='strings_vae64' else 44100))
                if not self._load_decoder(torch,codec_kind,codec_sr): return False
                m=BalladFlowRenderer(latent_ch=latent_ch,**cfg).to(self.device).eval(); m.load_state_dict(ck.get('ema',ck['model']),strict=True)
                m.latent_hz=latent_hz; m.codec_kind=codec_kind; m.codec_sample_rate=codec_sr
                self.models[key]=m; self.model_meta[key]={'latent_ch':latent_ch,'latent_hz':latent_hz,'codec_kind':codec_kind,'codec_sample_rate':codec_sr,'sampling_family':str(ck.get('sampling_family','rectified_flow')),'supported_steps':[int(x) for x in ck.get('supported_steps',[])],'recommended_steps':int(ck.get('recommended_steps',0) or 0)}; self.model_paths[int(mode)]=key
            else:
                meta=self.model_meta.get(key,{})
                if not self._load_decoder(torch,meta.get('codec_kind',self._manifest_codec_kind()),meta.get('codec_sample_rate',44100)): return False
                self.model_paths[int(mode)]=key
            self._error=''; return True
        except Exception as e:
            self._error=f'{type(e).__name__}: {e}'; return False
    def _model_for_mode(self, mode):
        mode=int(mode)
        key=self.model_paths.get(mode)
        if key and key in self.models: return self.models[key]
        if not self.load(mode): raise RuntimeError(self._error)
        return self.models[self.model_paths[mode]]

    @staticmethod
    def _speed_profile(v):
        # VST normalized 0/1/3, 1/3, 2/3, 1 from StringListParameter
        return float(max(0.0,min(1.0,v)))

    def _build_part_controls(self, req, events, part):
        torch=self.torch; sr=float(req.sample_rate); dur=max(0.08,(req.end_sample-req.start_sample)/sr)
        fps=100; N=max(8,int(math.ceil(dur*fps))); time=np.arange(N)/fps
        pitch=np.zeros(N,np.float32); gate=np.zeros(N,np.float32); onset=np.zeros(N,np.float32); vel=np.full(N,.7,np.float32)
        dyn=np.full(N,.62,np.float32); vib=np.full(N,.50,np.float32); exp=np.full(N,.90,np.float32); leg=np.ones(N,np.float32)
        pb=np.full(N,.50,np.float32); trans=np.full(N,.50,np.float32); tight=np.full(N,.50,np.float32); attack=np.full(N,.38,np.float32); speed=np.zeros(N,np.float32)
        art=np.zeros(N,np.int64); expr_stack=np.zeros(N,np.uint8); room=np.full(N,.18,np.float32)
        # event controls: dyn,vib,exp,vol,pan,sus,leg,room,bend,art,transition,tightness,attack,speed
        notes=[]; active=None; last_ctrl=None
        pe=[e for e in sorted(events,key=lambda x:x['project_sample']) if e['part']==part or e['type']==5]
        pe=apply_ensemble_event_timing_v44(pe,sr)
        for e in pe:
            ps=int(e['project_sample']); before=ps<int(req.start_sample)
            idx=int(max(0,min(N-1, round((ps-req.start_sample)/sr*fps))))
            c=e['controls']; last_ctrl=c
            dyn[idx:]=c[0]; vib[idx:]=c[1]; exp[idx:]=c[2]; leg[idx:]=c[6]; room[idx:]=c[7]; pb[idx:]=c[8]; art[idx:]=int(round(c[9]*11)); trans[idx:]=c[10]; tight[idx:]=c[11]; attack[idx:]=c[12]; speed[idx:]=c[13]
            packed=int(e.get('articulation',0));base_art=packed&0x0F;stack_bits=(packed>>4)&0x0F
            if int(e['type']) in (1,3,4):
                if 0<=base_art<12: art[idx:]=base_art
                expr_stack[idx:]=stack_bits
            if e['type']==1:
                if active is not None:
                    active['off']=idx;active['off_sample']=ps
                active={'note':e['note'],'on':0 if before else idx,'off':N,'vel':e['velocity'],'preexisting':before,
                        'on_sample':ps,'off_sample':int(req.end_sample)}; notes.append(active)
            elif e['type']==2 and active is not None and active['note']==e['note']:
                active['off']=max(active['on'],idx);active['off_sample']=ps;active=None
        dyn,vib,exp,leg,pb,trans,tight,attack,speed=smooth_voice_controls_v45(
            pe,req.start_sample,req.end_sample,sr,fps,(dyn,vib,exp,leg,pb,trans,tight,attack,speed))
        for n in notes:
            a,b=n['on'],min(N,n['off']);
            if b>a:
                pitch[a:b]=n['note']; gate[a:b]=1.; vel[a:b]=n['vel']
                if not n.get('preexisting',False): onset[a:min(N,a+2)]=1.
        note_prog=np.zeros(N,np.float32); dur_beats=np.zeros(N,np.float32); prev_int=np.zeros(N,np.float32); next_int=np.zeros(N,np.float32)
        for j,n in enumerate(notes):
            a,b=n['on'],min(N,n['off']); L=max(1,b-a); note_prog[a:b]=np.linspace(0,1,L,endpoint=False,dtype=np.float32)
            bpm=max(24.,float(req.tempo_bpm)); dur_beats[a:b]=(L/fps)*bpm/60.
            if j: prev_int[a:b]=float(n['note']-notes[j-1]['note'])
            if j+1<len(notes): next_int[a:b]=float(notes[j+1]['note']-n['note'])
        phrase=np.linspace(0,1,N,dtype=np.float32)
        policy=decode_flags(int(req.flags))
        assist_level=policy.assist_level; assist_strength=(0.0,0.60,1.0)[min(2,assist_level)]
        # v2.1 Clean-Room parity: context predicts performance but the authored CC/articulation
        # remains the anchor. Manual mode is bit-identical.
        dyn=predictive_dynamics(dyn,pitch,gate,onset,note_prog,phrase,prev_int,next_int,float(req.tempo_bpm),policy)
        art=smart_articulation_curve(art,gate,onset,dur_beats,leg,prev_int,next_int,float(req.tempo_bpm),policy)
        dyn,attack,tight,trans=articulation_stack_modifiers(art,dyn,attack,tight,trans,policy,expr_stack)
        # Manual keeps hidden bow intervention restrained; Assist/Auto progressively allow
        # the learned bow expert to contribute while written MIDI/CC remains authoritative.
        bow=np.clip(onset*(.18+.37*assist_strength) + (1-leg)*onset*(.10+.25*assist_strength),0,1).astype(np.float32)
        # v1.7 frontier: zero-weight Q4 hidden-physics coordination. It can coordinate
        # re-bow intent and de-lock vibrato bloom timing, but never rewrites CC3 or score data.
        vib_on=np.zeros(N,np.float32)
        bow,vib_on=coordinate_hidden_ensemble(bow,vib_on,gate,onset,events,part,req.start_sample,req.end_sample,sr,assist_strength,fps=fps)
        # v2.8/v3.0 parity: each desk gets deterministic micro-drift while remaining anchored
        # to the same authored phrase. This mirrors the NumPy/ORT control path.
        if policy.ensemble_looseness>0:
            phase=(part+1)*1.61803398875
            drift=np.sin(np.linspace(0,6.2831853,N,dtype=np.float32)+phase)*(.035*policy.ensemble_looseness)
            bow=np.clip(bow+drift,0,1); vib_on=np.clip(vib_on-drift*.55,0,1)
        # v1.8: deterministic look-back phrase memory + quartet feature bus. The model's
        # adapter is zero-start, so legacy/frontier checkpoints without it ignore this tensor.
        frontier_ctx,phrase=frontier_context_curves(events,part,req.start_sample,req.end_sample,sr,float(req.tempo_bpm),dyn,vib,leg,fps=fps)
        bpm=np.full(N,float(req.tempo_bpm),np.float32); spb=np.full(N,60./max(24.,float(req.tempo_bpm)),np.float32)
        trans_ms=np.zeros(N,np.float32); vd=np.zeros(N,np.float32); vr=np.zeros(N,np.float32); vj=np.zeros(N,np.float32); timing=np.zeros(N,np.float32)
        dyn,attack,trans,vib_on=phrase_director_curve(dyn,attack,trans,vib_on,phrase,note_prog,next_int,gate,policy)
        phys=physical_curves(pe,req.start_sample,sr,fps,N)
        phys=smooth_physical_curves_v45(phys,pe,req.start_sample,req.end_sample,sr,fps)
        if phys is not None:
            dyn,vib,exp,leg,trans,tight,attack,bow,pb=apply_string_physical_residuals(
                dyn,vib,exp,leg,trans,tight,attack,bow,pb,phys,gate,onset)
        porta_curve=None if phys is None else phys.get(118)
        pitch,gate,onset,note_prog,leg,trans,vib,vib_on,pb,trans_ms,_transition_links=apply_continuous_transition_paths_v46(
            notes,pitch,gate,onset,note_prog,leg,trans,vib,vib_on,pb,pe,
            req.start_sample,req.end_sample,sr,fps,porta_curve)
        dyn,vib,exp,attack,tight,bow,vib_on,vib_depth_cents,vib_rate_hz,phrase_momentum,_phrase_windows=apply_phrase_longline_v47(
            dyn,vib,exp,attack,tight,bow,vib_on,pe,req.start_sample,req.end_sample,sr,fps)
        lane_id=next((int(e.get('voice_lane',-1)) for e in pe if int(e.get('voice_lane',-1))>=0),-1)
        retake_identity=part if lane_id<0 else part+4*(lane_id+1)
        ret=apply_targeted_retake({'dynamics':dyn,'attack_character':attack,'short_tightness':tight,'bow_change_prob':bow,'vibrato_onset':vib_on,'vibrato_jitter':vj,'pitchbend':pb,'transition_speed':trans,'timing_feel':timing},self.fingerprint(),retake_identity,policy)
        dyn=ret['dynamics'];attack=ret['attack_character'];tight=ret['short_tightness'];bow=ret['bow_change_prob'];vib_on=ret['vibrato_onset'];vj=ret['vibrato_jitter'];pb=ret['pitchbend'];trans=ret['transition_speed'];timing=ret['timing_feel']
        ones=np.ones(N,np.float32); zeros=np.zeros(N,np.float32)
        def T(x): return torch.from_numpy(np.asarray(x)).unsqueeze(0).to(self.device)
        ins=0 if part<2 else (1 if part==2 else 2)
        return dict(pitch=T(pitch),gate=T(gate),onset=T(onset),velocity=T(vel),dynamics=T(dyn),vibrato=T(vib),expression=T(exp),legato=T(leg),pitchbend=T(pb),
                    transition_speed=T(trans),short_tightness=T(tight),attack_character=T(attack),note_progress=T(note_prog),phrase_position=T(phrase),prev_interval=T(prev_int),next_interval=T(next_int),bow_change_prob=T(bow),vibrato_onset=T(vib_on),tempo_bpm=T(bpm),seconds_per_beat=T(spb),note_duration_beats=T(dur_beats),transition_target_ms=T(trans_ms),speed_profile=T(speed),vibrato_depth_cents=T(vib_depth_cents),vibrato_rate_hz=T(vib_rate_hz),vibrato_jitter=T(vj),dynamics_known=T(ones),vibrato_known=T(ones),expression_known=T(ones),legato_known=T(ones),pitchbend_known=T(ones),timing_known=T(zeros),articulation_known=T(ones),vibrato_physics_known=T((vib_rate_hz>0).astype(np.float32)),frontier_context=torch.from_numpy(frontier_ctx).unsqueeze(0).to(self.device),instrument=torch.tensor([ins],device=self.device),articulation=torch.tensor([int(art[0])],device=self.device),player=torch.tensor([part],device=self.device),articulation_curve=T(art.astype(np.float32)))

    @staticmethod
    def _slice_controls(controls, start_s, end_s, total_s):
        """Slice frame curves for a long-audio tile; keep scalar IDs untouched."""
        out={}
        total=max(1e-6,float(total_s))
        for key,value in controls.items():
            if hasattr(value,'ndim') and value.ndim>=2 and value.shape[1]>1:
                n=int(value.shape[1])
                a=max(0,min(n-1,int(math.floor(float(start_s)/total*n))))
                b=max(a+1,min(n,int(math.ceil(float(end_s)/total*n))))
                out[key]=value[:,a:b]
            else:
                out[key]=value
        return out

    def _decode_latent(self, latent, sr, target_frames):
        torch=self.torch
        if self.decoder is None: raise RuntimeError('decoder is not loaded')
        y=self.decoder.decode(latent.float()) if hasattr(self.decoder,'decode') else self.decoder(latent.float())
        if y.ndim==3: y=y[:,0]
        y=y[0].float()
        host_len=max(1,int(round(y.numel()*int(sr)/float(self.codec_sample_rate))))
        if host_len!=y.numel():
            y=torch.nn.functional.interpolate(y[None,None],size=host_len,mode='linear',align_corners=False)[0,0]
        target_frames=max(1,int(target_frames))
        y=y[:target_frames]
        if y.numel()<target_frames: y=torch.nn.functional.pad(y,(0,target_frames-y.numel()))
        return y

    @staticmethod
    def _latent_shape(model, seconds):
        latent_hz=float(getattr(model,'latent_hz',25.0)); latent_ch=int(getattr(model,'latent_ch',1024))
        return latent_ch,max(2,int(math.ceil(max(.04,float(seconds))*latent_hz)))

    @staticmethod
    def _controls_digest(controls):
        h=hashlib.sha256()
        for key in sorted(controls):
            value=controls[key]; h.update(key.encode('utf-8')); h.update(b'\0')
            if hasattr(value,'detach'):
                a=value.detach().contiguous().cpu().numpy()
                h.update(str(a.dtype).encode()); h.update(str(tuple(a.shape)).encode()); h.update(a.tobytes())
            else:
                h.update(repr(value).encode('utf-8'))
        return h.hexdigest()

    def _tile_key(self, controls, sr, frames, nsteps, guidance_scale, part, absolute_start):
        raw='|'.join([self.fingerprint(),self._controls_digest(controls),str(int(sr)),str(int(frames)),
                      str(int(nsteps)),f'{float(guidance_scale):.5f}',str(int(part)),str(int(absolute_start))])
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def _render_tile(self, model, controls, sr, frames, nsteps, guidance_scale, seed, cache_key=None):
        torch=self.torch
        if cache_key:
            cached=self.tile_cache.get(cache_key,frames)
            if cached is not None:
                self.tile_cache_hits+=1
                return torch.from_numpy(cached).to(self.device)
            self.tile_cache_misses+=1
        dur=max(.04,float(frames)/float(sr)); latent_ch,tlat=self._latent_shape(model,dur)
        gen=torch.Generator(device=self.device); gen.manual_seed(int(seed)&0x7fffffffffffffff)
        x=torch.randn(1,latent_ch,tlat,device=self.device,generator=gen)
        x=sample_rectified_flow(model,x,controls,steps=nsteps,solver=self.solver,guidance_scale=guidance_scale)
        y=self._decode_latent(x,sr,frames)
        if cache_key: self.tile_cache.put(cache_key,y.detach().float().cpu().numpy())
        return y

    def _render_part_tiled(self, model, controls, sr, total_frames, nsteps, guidance_scale, base_seed, part, absolute_start=0):
        torch=self.torch
        total_frames=max(1,int(total_frames)); total_s=total_frames/float(sr)
        tile_frames=max(1,int(round(self.tile_seconds*sr)))
        overlap_frames=max(0,int(round(self.tile_overlap*sr)))
        if total_frames<=tile_frames or overlap_frames<=0:
            key=self._tile_key(controls,sr,total_frames,nsteps,guidance_scale,part,absolute_start)
            seed=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'little')
            return self._render_tile(model,controls,sr,total_frames,nsteps,guidance_scale,seed,cache_key=key)
        stride=max(1,tile_frames-overlap_frames)
        out=torch.zeros(total_frames,device=self.device,dtype=torch.float32)
        weight=torch.zeros(total_frames,device=self.device,dtype=torch.float32)
        start=0; tile_index=0
        while start<total_frames:
            end=min(total_frames,start+tile_frames); frames=end-start
            c=self._slice_controls(controls,start/float(sr),end/float(sr),total_s)
            key=self._tile_key(c,sr,frames,nsteps,guidance_scale,part,int(absolute_start)+start)
            seed=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'little')
            y=self._render_tile(model,c,sr,frames,nsteps,guidance_scale,seed,cache_key=key)
            w=torch.ones(frames,device=self.device,dtype=torch.float32)
            fade=min(overlap_frames,frames//2)
            if fade>1 and start>0:
                phase=torch.linspace(0.0,math.pi/2,fade,device=self.device)
                w[:fade]=torch.sin(phase).square()
            if fade>1 and end<total_frames:
                phase=torch.linspace(0.0,math.pi/2,fade,device=self.device)
                w[-fade:]=torch.cos(phase).square()
            out[start:end]+=y.float()*w; weight[start:end]+=w
            if end>=total_frames: break
            start+=stride; tile_index+=1
        return out/weight.clamp_min(1e-6)

    def _stable_render_seed(self, req, events):
        payload={'start':int(req.start_sample),'end':int(req.end_sample),'sr':int(req.sample_rate),
                 'parts':int(req.part_count),'mode':int(req.mode),'tempo':float(req.tempo_bpm),
                 'flags':int(req.flags),'events':events,'model':self.fingerprint()}
        raw=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')
        return int.from_bytes(hashlib.sha256(raw).digest()[:8],'little')

    def _effective_steps(self, model, requested):
        key=next((k for k,v in self.models.items() if v is model),None)
        meta=self.model_meta.get(key,{}) if key else {}
        if str(meta.get('sampling_family','rectified_flow')).lower()!='shortcut': return max(1,int(requested))
        supported=sorted(set(int(x) for x in (meta.get('supported_steps') or []) if int(x)>0))
        rec=int(meta.get('recommended_steps',0) or 0)
        desired=rec if rec>0 else max(1,int(requested))
        if not supported: return desired
        return min(supported,key=lambda x:(abs(x-desired),x))

    @staticmethod
    def _room_amount(events, part):
        vals=[]
        for e in events:
            if int(e.get('part',-1))==part and e.get('controls') and len(e['controls'])>7:
                vals.append(float(e['controls'][7]))
        return float(np.clip(np.median(vals) if vals else .18,0,1))

    def render(self, req, events):
        model=self._model_for_mode(req.mode)
        torch=self.torch; sr=int(req.sample_rate); total_frames=max(1,int(req.end_sample-req.start_sample))
        mix=None; base_seed=self._stable_render_seed(req,events); policy=decode_flags(int(req.flags))
        requested_steps=self.auto_steps if int(req.mode)==1 else self.steps
        nsteps=self._effective_steps(model,requested_steps)
        guidance=self.auto_cfg_scale if int(req.mode)==1 else self.cfg_scale
        ctx=torch.inference_mode()
        with ctx:
            for part in range(min(4,int(req.part_count))):
                lanes=allocate_polyphonic_event_lanes(events,part,max_voices=16) if policy.polyphony else [[e for e in events if int(e.get('part',-1))==part or int(e.get('type',0))==5]]
                if not lanes: continue
                for voice_idx,lane in enumerate(lanes):
                    controls=self._build_part_controls(req,lane,part)
                    if float(controls['gate'].max())<=0: continue
                    if self.device=='cuda':
                        with torch.autocast(device_type='cuda',dtype=torch.bfloat16,enabled=torch.cuda.is_bf16_supported()):
                            y=self._render_part_tiled(model,controls,sr,total_frames,nsteps,guidance,base_seed+voice_idx*7919,part,absolute_start=req.start_sample)
                    else:
                        y=self._render_part_tiled(model,controls,sr,total_frames,nsteps,guidance,base_seed+voice_idx*7919,part,absolute_start=req.start_sample)
                    # v2.1 independent voice spread prevents phase-locked unisons while preserving score pitch.
                    base_pan=[-.45,-.15,.12,.38][part]; spread=(voice_idx-(len(lanes)-1)*.5)*.055
                    pan=float(np.clip(base_pan+spread,-.92,.92)); gl=math.sqrt(.5*(1-pan)); gr=math.sqrt(.5*(1+pan))
                    dry=y*(1.0/max(1.0,math.sqrt(len(lanes))))
                    if policy.multi_out:
                        stage=render_stage_bundle(dry,sr,self._room_amount(lane,part),policy.stage_perspective)
                        # Apply traditional orchestral seating as an outer balance to every stereo pair.
                        st=stage.clone()
                        for pair in range(st.shape[1]//2):
                            st[:,pair*2]*=gl; st[:,pair*2+1]*=gr
                    else:
                        stage=mix_virtual_stage(dry,sr,self._room_amount(lane,part),policy.stage_perspective)
                        st=torch.stack([stage[:,0]*gl,stage[:,1]*gr],-1)
                    mix=st if mix is None else mix+st
        channels=34 if policy.multi_out else 2
        if mix is None: return np.zeros((total_frames,channels),np.float32)
        return mix.clamp(-.98,.98).cpu().numpy().astype(np.float32)

