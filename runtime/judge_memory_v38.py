"""SONICRAFT v3.8 local Judge Memory / Personal Taste Layer.

Small, explainable online preference correction over v3.7 objective DSP scores.
No audio, MIDI, identity or cloud data is stored. Profile is local JSON only.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, json, math, os, tempfile, threading
import numpy as np

DIMS=('dynamics','attack','transition','stability','safety')
EVENT_WEIGHT={'favorite':0.75,'reject':0.65,'commit':1.35}
PROFILE_VERSION=1

@dataclass(frozen=True)
class PreferenceProfile:
    evidence: float
    confidence: float
    weights: tuple[float,float,float,float,float]
    generation: int
    profile_hash: int

class JudgeMemory:
    def __init__(self,path):
        self.path=Path(path)
        self.lock=threading.Lock()
        self.evidence=0.0
        self.weights=np.zeros(5,np.float64)
        self.generation=0
        self._load()

    @staticmethod
    def _confidence(evidence):
        # Deliberately slow learning: evidence=1.35 (one manual commit) ~= 9.86% confidence.
        return float(np.clip(1.0-math.exp(-max(0.0,float(evidence))/13.0),0.0,1.0))

    def _payload(self):
        return {'version':PROFILE_VERSION,'evidence':float(self.evidence),
                'weights':[float(x) for x in self.weights], 'generation':int(self.generation)}

    @staticmethod
    def _hash_payload(payload):
        raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode('utf-8')
        return int.from_bytes(hashlib.sha256(raw).digest()[:8],'little')

    def snapshot(self):
        with self.lock:
            p=self._payload()
            return PreferenceProfile(float(self.evidence),self._confidence(self.evidence),
                                     tuple(float(x) for x in self.weights),int(self.generation),self._hash_payload(p))

    def _load(self):
        try:
            obj=json.loads(self.path.read_text(encoding='utf-8'))
            if int(obj.get('version',0))!=PROFILE_VERSION:return
            w=np.asarray(obj.get('weights',[]),np.float64)
            if w.shape!=(5,) or not np.isfinite(w).all():return
            self.evidence=max(0.0,float(obj.get('evidence',0.0)))
            self.weights=np.clip(w,-1.0,1.0)
            self.weights[4]=max(0.0,self.weights[4]) # Safety can never be learned as a negative preference.
            self.generation=max(0,int(obj.get('generation',0)))
        except Exception:
            return

    def _save_atomic(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload=json.dumps(self._payload(),sort_keys=True,indent=2)+'\n'
        fd,tmp=tempfile.mkstemp(prefix=self.path.name+'.',suffix='.tmp',dir=str(self.path.parent))
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                f.write(payload); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            try: os.unlink(tmp)
            except FileNotFoundError: pass

    @staticmethod
    def _features(scores):
        # scores: 4x6 [overall,dynamics,attack,transition,stability,safety]
        a=np.asarray(scores,np.float64)
        if a.shape!=(4,6) or not np.isfinite(a).all():raise ValueError('scores must be 4x6 finite')
        return a[:,1:6]

    def learn(self,kind,selected_take,scores):
        kind=str(kind).lower()
        if kind not in EVENT_WEIGHT:raise ValueError('unknown preference event')
        take=int(selected_take)
        if take<0 or take>3:raise ValueError('take out of range')
        feat=self._features(scores)
        others=np.mean(np.delete(feat,take,axis=0),axis=0)
        delta=np.clip(feat[take]-others,-1.0,1.0)
        polarity=-1.0 if kind=='reject' else 1.0
        ev=EVENT_WEIGHT[kind]
        # Bounded online update; more evidence reduces the step size.
        with self.lock:
            lr=0.24/(1.0+self.evidence/10.0)
            self.weights=np.clip(self.weights + polarity*lr*ev*delta,-1.0,1.0)
            self.weights[4]=max(0.0,self.weights[4])
            self.evidence+=ev
            self.generation+=1
            self._save_atomic()
            p=self._payload()
            return PreferenceProfile(self.evidence,self._confidence(self.evidence),tuple(float(x) for x in self.weights),self.generation,self._hash_payload(p))

    def clear(self):
        with self.lock:
            self.evidence=0.0; self.weights[:]=0.0; self.generation+=1
            try:self.path.unlink()
            except FileNotFoundError:pass
            p=self._payload()
            return PreferenceProfile(0.0,0.0,(0,0,0,0,0),self.generation,self._hash_payload(p))

    def personalize(self,scores,enabled=True,strength=1.0,favorite_mask=0,reject_mask=0):
        a=np.asarray(scores,np.float64)
        feat=self._features(a)
        snap=self.snapshot()
        strength=float(np.clip(strength,0,1)) if enabled else 0.0
        # Center features across A-D so profile changes ranking, not absolute loudness/quality scale.
        centered=feat-np.mean(feat,axis=0,keepdims=True)
        raw=centered@np.asarray(snap.weights,np.float64)/5.0
        # Personal correction cannot dominate objective Judge: max +/- 0.12 at full confidence/strength.
        bonus=np.clip(raw,-1,1)*0.12*snap.confidence*strength
        # Unsafe takes cannot receive a positive taste bonus.
        bonus=np.where(feat[:,4]<0.20,np.minimum(bonus,0.0),bonus)
        personal=np.clip(a[:,0]+bonus,0,1)
        best=-1;best_rank=-1e9
        for i in range(4):
            bit=1<<i
            if int(reject_mask)&bit:continue
            rank=float(personal[i])+(1.25 if int(favorite_mask)&bit else 0.0)
            if rank>best_rank:best_rank=rank;best=i
        return best,personal,snap

    def decision(self,scores,enabled=True,strength=1.0,favorite_mask=0,reject_mask=0,
                 min_confidence=0.25,min_margin=0.035,safety_floor=0.35):
        winner,personal,snap=self.personalize(scores,enabled,strength,favorite_mask,reject_mask)
        if winner<0:return {'winner':-1,'commit':False,'reason':'no_viable_take','margin':0.0,'profile':snap,'personal':personal}
        viable=[float(personal[i]) for i in range(4) if not (int(reject_mask)&(1<<i))]
        viable.sort(reverse=True)
        margin=viable[0]-(viable[1] if len(viable)>1 else 0.0)
        safety=float(np.asarray(scores)[winner,5])
        ok=(snap.confidence>=float(min_confidence) and margin>=float(min_margin) and safety>=float(safety_floor))
        reason='high_confidence' if ok else ('low_profile_confidence' if snap.confidence<float(min_confidence) else ('low_margin' if margin<float(min_margin) else 'safety_floor'))
        return {'winner':winner,'commit':bool(ok),'reason':reason,'margin':float(margin),'profile':snap,'personal':personal}
