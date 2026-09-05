"""SONICRAFT v4.9 local Repair Policy Memory.

Stores only a few bounded repair-strategy multipliers and aggregate evidence.
No audio, MIDI, score text, identity, filenames, or cloud data is stored.

Learning is deliberately gated:
- all A/B/C/D renders must be present and comparable,
- Audio Judge winner margin >= 0.025,
- winner safety >= 0.35,
- winner overall >= 0.35,
- stale policy generation/hash is rejected by the iteration orchestrator.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,math,os,sys,tempfile

PROFILE_VERSION=1
KEYS=("smoothing","bow_relief","transition","ensemble_tightness","expressive_apex")
DEFAULT={k:1.0 for k in KEYS}
TARGETS={
    "A":{"smoothing":.84,"bow_relief":.90,"transition":.90,"ensemble_tightness":.92,"expressive_apex":.90},
    "B":{"smoothing":1.18,"bow_relief":1.17,"transition":1.18,"ensemble_tightness":1.18,"expressive_apex":.88},
    "C":{"smoothing":1.02,"bow_relief":.95,"transition":1.00,"ensemble_tightness":.94,"expressive_apex":1.22},
    "D":{"smoothing":.78,"bow_relief":.80,"transition":.82,"ensemble_tightness":.86,"expressive_apex":.86},
}
MIN_MARGIN=.025
SAFETY_FLOOR=.35
OVERALL_FLOOR=.35

def default_policy_path():
    if sys.platform.startswith("win"):
        base=Path(os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or Path.home())
    elif sys.platform=="darwin":
        base=Path.home()/"Library"/"Application Support"
    else:
        base=Path(os.environ.get("XDG_STATE_HOME") or (Path.home()/".local"/"state"))
    return base/"SONICRAFT_AI_Strings"/"repair_policy_v49.json"

def _clamp(x):return max(.65,min(1.35,float(x)))

@dataclass(frozen=True)
class RepairPolicySnapshotV49:
    evidence:float
    confidence:float
    generation:int
    values:dict
    profile_hash:str

class RepairPolicyMemoryV49:
    def __init__(self,path=None):
        self.path=Path(path) if path else default_policy_path()
        self.evidence=0.0;self.generation=0;self.values=dict(DEFAULT)
        self._load()

    @staticmethod
    def _confidence(e):
        return max(0.0,min(1.0,1.0-math.exp(-max(0.0,float(e))/10.0)))

    def _payload(self):
        return {"version":PROFILE_VERSION,"evidence":round(float(self.evidence),9),
                "generation":int(self.generation),"values":{k:round(float(self.values[k]),9) for k in KEYS}}

    @staticmethod
    def _hash(payload):
        raw=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
        return hashlib.sha256(raw).hexdigest()[:24]

    def snapshot(self):
        p=self._payload()
        return RepairPolicySnapshotV49(self.evidence,self._confidence(self.evidence),self.generation,
                                       dict(self.values),self._hash(p))

    def _load(self):
        try:
            o=json.loads(self.path.read_text(encoding="utf-8"))
            if int(o.get("version",0))!=PROFILE_VERSION:return
            vals=o.get("values",{})
            if not all(k in vals for k in KEYS):return
            self.values={k:_clamp(vals[k]) for k in KEYS}
            self.evidence=max(0.0,float(o.get("evidence",0.0)))
            self.generation=max(0,int(o.get("generation",0)))
        except Exception:return

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(self._payload(),sort_keys=True,indent=2)+"\n"
        fd,tmp=tempfile.mkstemp(prefix=self.path.name+".",suffix=".tmp",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            try:os.unlink(tmp)
            except FileNotFoundError:pass

    def learn(self,winner_slot,margin,winner_safety,winner_overall):
        slot=str(winner_slot).upper()
        if slot not in TARGETS:return {"learned":False,"reason":"invalid_winner","snapshot":self.snapshot()}
        margin=float(margin);safety=float(winner_safety);overall=float(winner_overall)
        if margin<MIN_MARGIN:return {"learned":False,"reason":"low_margin","snapshot":self.snapshot()}
        if safety<SAFETY_FLOOR:return {"learned":False,"reason":"safety_floor","snapshot":self.snapshot()}
        if overall<OVERALL_FLOOR:return {"learned":False,"reason":"low_overall","snapshot":self.snapshot()}
        # Bounded slow update. One result can move a multiplier by at most ~0.06.
        alpha=min(.16,.035+margin*.55)
        target=TARGETS[slot]
        before=dict(self.values)
        for k in KEYS:
            self.values[k]=_clamp(self.values[k]+alpha*(target[k]-self.values[k]))
        self.evidence+=min(1.5,.55+margin*4.0)
        self.generation+=1
        self._save()
        return {"learned":True,"reason":"accepted","winner":slot,"alpha":alpha,
                "before":before,"after":dict(self.values),"snapshot":self.snapshot()}

    def clear(self):
        self.values=dict(DEFAULT);self.evidence=0.0;self.generation+=1
        try:self.path.unlink()
        except FileNotFoundError:pass
        return self.snapshot()
