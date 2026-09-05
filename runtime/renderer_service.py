from __future__ import annotations
import argparse, hashlib, json, os, socket, struct, sys, threading, time
from pathlib import Path
import numpy as np
from protocol import *
from model_backend import MockBackend, TorchFlowBackend
from ort_model_backend import ORTFlowBackend
from runtime_backend_selector_v24 import select_backend
from audio_take_judge_v37 import rank_takes
from judge_memory_v38 import JudgeMemory

MAX_EVENTS=32768
MAX_RENDER_SECONDS=45

class RendererService:
    def __init__(self, host='127.0.0.1', port=49337, model_dir=None, cache_dir=None, mock=False, steps=24, auto_steps=8, cache_gb=4.0, solver='euler', cfg_scale=1.0, auto_cfg_scale=1.0, tile_seconds=10.0, tile_overlap=1.0, backend='auto'):
        installed_home = Path(__file__).resolve().parent.parent
        if not (installed_home / 'install-location.json').exists():
            env_home = os.getenv('SONICRAFT_AI_STRINGS_HOME','').strip()
            installed_home = Path(env_home) if env_home else Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'SONICRAFT'/'AI Strings Q4'
        self.host=host; self.port=int(port); self.model_dir=Path(model_dir) if model_dir else installed_home/'Models'
        self.cache_dir=Path(cache_dir) if cache_dir else installed_home/'Cache'
        self.cache_dir.mkdir(parents=True,exist_ok=True)
        self.profile_dir=installed_home/'Profiles'; self.profile_dir.mkdir(parents=True,exist_ok=True)
        self.judge_memory=JudgeMemory(self.profile_dir/'judge_memory_v38.json')
        requested=str(backend or os.getenv('SONICRAFT_RUNTIME','auto')).strip().lower()
        if requested not in ('auto','torch','ort'): requested='auto'
        runtime_choice,selection_detail=select_backend(installed_home,self.model_dir,requested)
        if mock:self.backend=MockBackend()
        elif runtime_choice=='ort':self.backend=ORTFlowBackend(self.model_dir,steps=steps,auto_steps=auto_steps,solver=solver,cfg_scale=cfg_scale,auto_cfg_scale=auto_cfg_scale)
        else:self.backend=TorchFlowBackend(self.model_dir,steps=steps,auto_steps=auto_steps,solver=solver,cfg_scale=cfg_scale,auto_cfg_scale=auto_cfg_scale,tile_seconds=tile_seconds,tile_overlap=tile_overlap,tile_cache_dir=self.cache_dir/'Tiles')
        self.runtime_selection_detail=selection_detail
        self.mock=bool(mock); self.render_lock=threading.Lock(); self.stop_evt=threading.Event(); self.sock=None
        self.cache_limit=max(256*1024*1024,int(float(cache_gb)*(1024**3))); self.last_prune=0.0
    def log(self,msg): print(time.strftime('%Y-%m-%d %H:%M:%S'),msg,flush=True)
    def parse_events(self, raw, count):
        out=[]; off=0
        for _ in range(count):
            tup=EVENT.unpack_from(raw,off); off+=EVENT.size
            ps,typ,wire_part,note,art,vel,tempo,*ctrl=tup
            if wire_part>=4:
                voice_lane=(int(wire_part)>>2)-1
                part=int(wire_part)&0x03
            else:
                voice_lane=-1
                part=int(wire_part)
            out.append({'project_sample':ps,'type':typ,'part':part,'voice_lane':voice_lane,'note':note,'articulation':art,'velocity':vel,'tempo_bpm':tempo,'controls':ctrl})
        return out
    def cache_key(self, hbytes, ebytes):
        h=unpack_request_header(hbytes); h.request_id=0
        fp=getattr(self.backend,'fingerprint',lambda:'mock-v1')().encode('ascii','ignore')
        return hashlib.sha256(fp+b'\0'+pack_request_header(h)+ebytes).hexdigest()
    def cache_paths(self,key): return self.cache_dir/(key+'.f32'), self.cache_dir/(key+'.json')
    def _read_cache(self,key,req):
        af,mf=self.cache_paths(key)
        if not (af.exists() and mf.exists()): return None
        try:
            meta=json.loads(mf.read_text(encoding='utf-8')); payload=af.read_bytes(); frames=int(meta['frames']); channels=int(meta.get('channels',2))
            if channels not in (2,24,34) or len(payload)!=frames*channels*4: return None
            return pack_response_header(ResponseHeader(STATUS_CACHE_HIT,req.request_id,req.start_sample,frames,req.sample_rate,channels,1,len(payload))),payload
        except Exception: return None
    def prune_cache(self,force=False):
        now=time.time()
        if not force and now-self.last_prune<60: return
        self.last_prune=now
        try:
            files=[p for p in self.cache_dir.glob('*.f32') if p.is_file()]
            total=sum(p.stat().st_size for p in files)
            if total<=self.cache_limit: return
            target=int(self.cache_limit*.85)
            for af in sorted(files,key=lambda p:p.stat().st_mtime):
                if total<=target: break
                try:
                    size=af.stat().st_size; af.unlink(missing_ok=True); af.with_suffix('.json').unlink(missing_ok=True); total-=size
                except OSError: pass
        except OSError: pass
    @staticmethod
    def _derive_take_nonce(base_nonce:float,take_index:int)->float:
        base=max(0.0,min(1.0,float(base_nonce))); idx=max(0,min(3,int(take_index)))
        if idx==0:return base
        q=int(round(base*16777215.0)) & 0xFFFFFFFF
        x=(q ^ ((0x9E3779B9*(idx+1))&0xFFFFFFFF))&0xFFFFFFFF
        x ^= x>>16; x=(x*0x7FEB352D)&0xFFFFFFFF; x ^= x>>15
        x=(x*0x846CA68B)&0xFFFFFFFF; x ^= x>>16
        return float(x & 0x00FFFFFF)/16777215.0

    @staticmethod
    def _flags_with_nonce(flags:int,nonce:float)->int:
        q=max(0,min(255,int(round(max(0.0,min(1.0,float(nonce)))*255.0))))
        return (int(flags)&~(0xFF<<11)) | (q<<11)

    def _handle_judge(self,c,req):
        if req.event_count>MAX_EVENTS or req.end_sample<=req.start_sample or (req.end_sample-req.start_sample)>req.sample_rate*MAX_RENDER_SECONDS:
            c.sendall(pack_response_header(ResponseHeader(STATUS_BAD_REQUEST,req.request_id,req.start_sample,0,req.sample_rate,0,0,0)));return
        cfg=recv_exact(c,JUDGE_CONFIG.size)
        base_nonce,favorite_mask,reject_mask,reserved=JUDGE_CONFIG.unpack(cfg)
        ebytes=recv_exact(c,EVENT.size*req.event_count)
        events=self.parse_events(ebytes,req.event_count)
        with self.render_lock:
            if not self.backend.status().ready and hasattr(self.backend,'load'): self.backend.load(req.mode)
            if not self.backend.status().ready:
                c.sendall(pack_response_header(ResponseHeader(STATUS_MODEL_NOT_READY,req.request_id,req.start_sample,0,req.sample_rate,0,0,0)));return
            try:
                audios=[]
                valid_mask=0
                for take in range(4):
                    nonce=self._derive_take_nonce(base_nonce,take)
                    take_req=RequestHeader(TYPE_RENDER,req.request_id*10+take,req.start_sample,req.end_sample,req.sample_rate,
                                           req.event_count,req.part_count,req.mode,req.tempo_bpm,req.lookahead,
                                           self._flags_with_nonce(req.flags,nonce))
                    take_hbytes=pack_request_header(take_req)
                    key=self.cache_key(take_hbytes,ebytes)
                    cached=self._read_cache(key,take_req)
                    if cached:
                        crh=unpack_response_header(cached[0])
                        audio=np.frombuffer(cached[1],dtype='<f4').reshape(crh.frames,crh.channels).copy()
                    else:
                        audio=np.asarray(self.backend.render(take_req,events),dtype='<f4',order='C')
                        if audio.ndim!=2 or audio.shape[1] not in (2,24,34): raise ValueError('judge backend render shape')
                        af,mf=self.cache_paths(key); payload=audio.tobytes(); tmp=af.with_suffix('.tmp');tmp.write_bytes(payload);os.replace(tmp,af)
                        mf.write_text(json.dumps({'frames':int(audio.shape[0]),'channels':int(audio.shape[1]),'sample_rate':take_req.sample_rate,
                            'backend':self.backend.status().name,'model_fingerprint':getattr(self.backend,'fingerprint',lambda:'mock-v1')()}),encoding='utf-8')
                    audios.append(audio);valid_mask|=1<<take
                self.prune_cache()
                objective_winner,scores=rank_takes(audios,req.sample_rate,events,req.start_sample,req.end_sample,
                                                    int(favorite_mask)&0x0F,int(reject_mask)&0x0F)
                vals=[]
                for s in scores: vals += [s.overall,s.dynamics,s.attack,s.transition,s.stability,s.safety]
                personal_cap=(int(reserved)&JUDGE_CAP_PERSONAL)!=0
                personal_enabled=(int(reserved)&JUDGE_PERSONAL_ENABLED)!=0
                strength=float(int(reserved)&JUDGE_STRENGTH_MASK)/255.0
                if personal_cap:
                    matrix=np.asarray(vals,dtype=np.float32).reshape(4,6)
                    winner,personal,profile=self.judge_memory.personalize(matrix,personal_enabled,strength,int(favorite_mask)&0x0F,int(reject_mask)&0x0F)
                    extra=[float(x) for x in personal]+[profile.confidence]+[float(x) for x in profile.weights]
                    payload=JUDGE_RESULT_V2.pack(JUDGE_RESULT_V2_VERSION,255 if winner<0 else winner,valid_mask,*(vals+extra),int(profile.profile_hash)&0xFFFFFFFF)
                    flags=(0 if winner<0 else (winner+1)) | ((valid_mask&0x0F)<<8) | (1<<15)
                else:
                    winner=objective_winner
                    payload=JUDGE_RESULT.pack(JUDGE_RESULT_VERSION,255 if winner<0 else winner,valid_mask,*vals)
                    flags=(0 if winner<0 else (winner+1)) | ((valid_mask&0x0F)<<8)
                c.sendall(pack_response_header(ResponseHeader(STATUS_OK,req.request_id,req.start_sample,4,req.sample_rate,0,flags,len(payload))))
                c.sendall(payload)
            except Exception as e:
                self.log(f'judge error: {type(e).__name__}: {e}')
                c.sendall(pack_response_header(ResponseHeader(STATUS_INTERNAL_ERROR,req.request_id,req.start_sample,0,req.sample_rate,0,0,0)))

    def _profile_payload(self):
        p=self.judge_memory.snapshot()
        return PROFILE_RESULT.pack(PROFILE_RESULT_VERSION,0,p.profile_hash,p.confidence,p.evidence,*p.weights)

    def _handle_preference(self,c,req):
        raw=recv_exact(c,PREFERENCE_EVENT.size)
        kind,take,_,*vals=PREFERENCE_EVENT.unpack(raw)
        kinds={1:'favorite',2:'reject',3:'commit'}
        if kind not in kinds or take>3:
            c.sendall(pack_response_header(ResponseHeader(STATUS_BAD_REQUEST,req.request_id,0,0,req.sample_rate,0,0,0)));return
        try:
            self.judge_memory.learn(kinds[kind],int(take),np.asarray(vals,dtype=np.float32).reshape(4,6))
            payload=self._profile_payload()
            c.sendall(pack_response_header(ResponseHeader(STATUS_OK,req.request_id,0,0,req.sample_rate,0,0,len(payload))));c.sendall(payload)
        except Exception as e:
            self.log(f'preference error: {type(e).__name__}: {e}')
            c.sendall(pack_response_header(ResponseHeader(STATUS_BAD_REQUEST,req.request_id,0,0,req.sample_rate,0,0,0)))

    def _handle_profile_query(self,c,req):
        payload=self._profile_payload()
        c.sendall(pack_response_header(ResponseHeader(STATUS_OK,req.request_id,0,0,req.sample_rate,0,0,len(payload))));c.sendall(payload)

    def _handle_profile_clear(self,c,req):
        self.judge_memory.clear();payload=self._profile_payload()
        c.sendall(pack_response_header(ResponseHeader(STATUS_OK,req.request_id,0,0,req.sample_rate,0,0,len(payload))));c.sendall(payload)

    def handle(self,c):
        hbytes=recv_exact(c,REQ_HEADER.size); req=unpack_request_header(hbytes)
        if req.msg_type==TYPE_PING:
            st=self.backend.status(); flags=1 if st.ready else 0
            name=str(getattr(st,'name','')).lower()
            if name.startswith('ort'): flags |= (1<<1)
            elif name.startswith('torch'): flags |= (1<<2)
            elif name.startswith('mock'): flags |= (1<<3)
            c.sendall(pack_response_header(ResponseHeader(STATUS_OK if st.ready else STATUS_MODEL_NOT_READY,req.request_id,0,0,req.sample_rate,0,flags,0))); return
        if req.msg_type==TYPE_PREFERENCE:
            self._handle_preference(c,req); return
        if req.msg_type==TYPE_PROFILE_QUERY:
            self._handle_profile_query(c,req); return
        if req.msg_type==TYPE_PROFILE_CLEAR:
            self._handle_profile_clear(c,req); return
        if req.msg_type==TYPE_JUDGE:
            self._handle_judge(c,req); return
        if req.msg_type!=TYPE_RENDER or req.event_count>MAX_EVENTS or req.end_sample<=req.start_sample or (req.end_sample-req.start_sample)>req.sample_rate*MAX_RENDER_SECONDS:
            c.sendall(pack_response_header(ResponseHeader(STATUS_BAD_REQUEST,req.request_id,req.start_sample,0,req.sample_rate,0,0,0))); return
        ebytes=recv_exact(c,EVENT.size*req.event_count); events=self.parse_events(ebytes,req.event_count); key=self.cache_key(hbytes,ebytes)
        cached=self._read_cache(key,req)
        if cached:
            c.sendall(cached[0]); c.sendall(cached[1]); return
        # GPU inference is serialized in one persistent service so four VST instances share one
        # copy of the models/decoder instead of racing four independent CUDA contexts. The TCP
        # accept loop itself remains responsive; waiting clients block only their worker thread.
        with self.render_lock:
            cached=self._read_cache(key,req)
            if cached:
                c.sendall(cached[0]); c.sendall(cached[1]); return
            if not self.backend.status().ready and hasattr(self.backend,'load'): self.backend.load(req.mode)
            if not self.backend.status().ready:
                c.sendall(pack_response_header(ResponseHeader(STATUS_MODEL_NOT_READY,req.request_id,req.start_sample,0,req.sample_rate,0,0,0))); return
            try:
                audio=self.backend.render(req,events); audio=np.asarray(audio,dtype='<f4',order='C')
                if audio.ndim!=2 or audio.shape[1] not in (2,24,34): raise ValueError('backend must return [frames,2], [frames,24] or [frames,34] float32')
                af,mf=self.cache_paths(key); payload=audio.tobytes(); tmp=af.with_suffix('.tmp'); tmp.write_bytes(payload); os.replace(tmp,af); mf.write_text(json.dumps({'frames':int(audio.shape[0]),'channels':int(audio.shape[1]),'sample_rate':req.sample_rate,'backend':self.backend.status().name,'model_fingerprint':getattr(self.backend,'fingerprint',lambda:'mock-v1')()}),encoding='utf-8')
                self.prune_cache()
                c.sendall(pack_response_header(ResponseHeader(STATUS_OK,req.request_id,req.start_sample,int(audio.shape[0]),req.sample_rate,int(audio.shape[1]),0,len(payload)))); c.sendall(payload)
            except Exception as e:
                self.log(f'render error: {type(e).__name__}: {e}')
                c.sendall(pack_response_header(ResponseHeader(STATUS_INTERNAL_ERROR,req.request_id,req.start_sample,0,req.sample_rate,0,0,0)))
    def _client_thread(self,c):
        with c:
            c.settimeout(120)
            try: self.handle(c)
            except Exception as e: self.log(f'client error: {type(e).__name__}: {e}')
    def run(self):
        # Warm AUTO once at service startup. HQ is loaded lazily only when it is actually used.
        # Missing/invalid weights are non-fatal: the VST remains on LIVE preview.
        if not self.mock and hasattr(self.backend,'load'):
            self.backend.load(1)
        st=self.backend.status(); self.log(f'backend={st.name} ready={st.ready} detail={st.detail} selection={getattr(self,"runtime_selection_detail","mock")}')
        self.prune_cache(force=True)
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind((self.host,self.port)); s.listen(16); s.settimeout(.5); self.sock=s
        self.log(f'listening on {self.host}:{self.port}')
        while not self.stop_evt.is_set():
            try: c,_=s.accept()
            except socket.timeout: continue
            except OSError: break
            threading.Thread(target=self._client_thread,args=(c,),daemon=True).start()
        s.close()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--host',default='127.0.0.1'); ap.add_argument('--port',type=int,default=49337); ap.add_argument('--model-dir'); ap.add_argument('--cache-dir'); ap.add_argument('--mock',action='store_true'); ap.add_argument('--steps',type=int,default=24,help='HQ rectified-flow steps'); ap.add_argument('--auto-steps',type=int,default=8,help='AUTO Compact rectified-flow steps'); ap.add_argument('--cache-gb',type=float,default=4.0)
    ap.add_argument('--solver',choices=['euler','heun'],default='euler'); ap.add_argument('--cfg-scale',type=float,default=1.0,help='HQ MIDI-authority guidance scale; benchmark before >1.0 promotion'); ap.add_argument('--auto-cfg-scale',type=float,default=1.0)
    ap.add_argument('--tile-seconds',type=float,default=10.0); ap.add_argument('--tile-overlap',type=float,default=1.0); ap.add_argument('--backend',choices=['auto','torch','ort'],default=os.getenv('SONICRAFT_RUNTIME','auto'))
    a=ap.parse_args(); RendererService(a.host,a.port,a.model_dir,a.cache_dir,a.mock,a.steps,a.auto_steps,a.cache_gb,a.solver,a.cfg_scale,a.auto_cfg_scale,a.tile_seconds,a.tile_overlap,a.backend).run()
if __name__=='__main__': main()
