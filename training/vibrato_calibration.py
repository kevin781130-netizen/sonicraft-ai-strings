from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path

DEFAULT_CC3 = [0.0, 32.0, 64.0, 96.0, 127.0]
DEFAULT_DEPTH = [0.0, 12.0, 28.0, 48.0, 72.0]
DEFAULT_RATE = {'slow':4.45,'normal':5.35,'fast':6.35}


def _interp(x, xs, ys):
    x=float(x)
    if x<=xs[0]: return float(ys[0])
    if x>=xs[-1]: return float(ys[-1])
    for i in range(len(xs)-1):
        if xs[i] <= x <= xs[i+1]:
            t=(x-xs[i]) / max(1e-9, xs[i+1]-xs[i])
            return float(ys[i] + t*(ys[i+1]-ys[i]))
    return float(ys[-1])


def _monotonic_depth(vals):
    v=[0.0]+[max(0.0,min(90.0,float(x))) for x in vals[1:]]
    floors=[0.0,6.0,12.0,20.0,30.0]
    for i in range(1,5):
        v[i]=max(v[i],floors[i],v[i-1]+3.0)
    if v[-1]>90.0:
        scale=90.0/v[-1]
        v=[0.0]+[max(floors[i],v[i]*scale) for i in range(1,5)]
        for i in range(1,5): v[i]=max(v[i],v[i-1]+2.0)
    return v

@dataclass
class VibratoCalibration:
    depth_cents: dict
    rate_hz: dict
    onset_ms: dict
    source_events: dict
    schema_version: int = 1

    @classmethod
    def default(cls):
        return cls({'all':list(DEFAULT_DEPTH)}, {'all':dict(DEFAULT_RATE)},
                   {'all':{'early':140.0,'natural':250.0,'late':390.0}}, {'all':0}, 1)

    @classmethod
    def load(cls,path: str|Path|None):
        if not path or not Path(path).exists(): return cls.default()
        d=json.loads(Path(path).read_text(encoding='utf-8'))
        return cls(d.get('depth_cents',{'all':DEFAULT_DEPTH}),d.get('rate_hz',{'all':DEFAULT_RATE}),
                   d.get('onset_ms',{'all':{'early':140,'natural':250,'late':390}}),
                   d.get('source_events',{}),int(d.get('schema_version',1)))

    def save(self,path: str|Path):
        p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({'schema_version':self.schema_version,'cc3_anchors':DEFAULT_CC3,
                                 'depth_cents':self.depth_cents,'rate_hz':self.rate_hz,
                                 'onset_ms':self.onset_ms,'source_events':self.source_events},
                                indent=2,sort_keys=True),encoding='utf-8')

    def _depth(self,instrument='all'):
        row=self.depth_cents.get(str(instrument)) or self.depth_cents.get('all') or DEFAULT_DEPTH
        return _monotonic_depth(list(row))

    def depth_to_cc3(self,depth_cents:float,instrument='all') -> float:
        return _interp(max(0.0,min(90.0,float(depth_cents))),self._depth(instrument),DEFAULT_CC3)/127.0

    def cc3_to_depth(self,cc3:float,instrument='all') -> float:
        x=float(cc3); x=x*127.0 if x<=1.0 else x
        return _interp(max(0.0,min(127.0,x)),DEFAULT_CC3,self._depth(instrument))
