from __future__ import annotations
from dataclasses import dataclass
from bisect import bisect_right

@dataclass(frozen=True)
class TempoPoint:
    beat: float
    bpm: float

class TempoTimeline:
    """Piecewise tempo timeline for CUDA/shadow render jobs.

    Beats are quarter-note project positions (VST3 ProcessContext.projectTimeMusic semantics).
    Points may be sampled densely during ramps; interpolation is linear between points.
    """
    def __init__(self, points):
        pts=sorted([(TempoPoint(float(p.beat),float(p.bpm)) if isinstance(p,TempoPoint) else TempoPoint(float(p[0]),float(p[1]))) for p in points], key=lambda p:p.beat)
        if not pts: pts=[TempoPoint(0.0,68.0)]
        self.points=pts; self.beats=[p.beat for p in pts]

    def bpm_at(self, beat: float) -> float:
        b=float(beat); i=bisect_right(self.beats,b)-1
        if i<0:return self.points[0].bpm
        if i>=len(self.points)-1:return self.points[-1].bpm
        a,z=self.points[i],self.points[i+1]
        if z.beat<=a.beat:return a.bpm
        t=max(0.0,min(1.0,(b-a.beat)/(z.beat-a.beat)))
        return max(24.0,min(300.0,a.bpm+t*(z.bpm-a.bpm)))

    def seconds_between(self, start_beat: float, end_beat: float, steps_per_beat: int=48) -> float:
        """Numerically integrate beat duration across tempo changes/ramps."""
        a,b=float(start_beat),float(end_beat)
        if b<a:return -self.seconds_between(b,a,steps_per_beat)
        if b==a:return 0.0
        n=max(1,int((b-a)*steps_per_beat+.999))
        h=(b-a)/n; total=0.0
        for i in range(n):
            x=a+(i+.5)*h; total += h*60.0/self.bpm_at(x)
        return total

    def framewise_bpm(self, start_beat: float, duration_beats: float, frames: int):
        if frames<=0:return []
        if frames==1:return [self.bpm_at(start_beat)]
        return [self.bpm_at(start_beat+duration_beats*i/(frames-1)) for i in range(frames)]

    def to_job_dict(self):
        return [{'beat':p.beat,'bpm':p.bpm} for p in self.points]
