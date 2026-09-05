from __future__ import annotations
from dataclasses import dataclass
import json, math
from pathlib import Path

SPEED_QUANTILE = {'auto': None, 'slow': 0.80, 'normal': 0.50, 'fast': 0.20}

# Conservative beat-domain priors used only until enough rights-cleared transition labels exist.
# Timing is represented in fractions of a quarter-note, then converted to milliseconds from
# the current Cubase tempo. This keeps Slow/Normal/Fast musically consistent across songs.
DEFAULT_BEAT_PRIORS = {
    'legato': {'slow': 0.145, 'normal': 0.095, 'fast': 0.060},
    'portamento': {'slow': 0.390, 'normal': 0.250, 'fast': 0.145},
    'bow_change': {'slow': 0.082, 'normal': 0.052, 'fast': 0.032},
}
PHYSICAL_MS_CLAMPS = {
    'legato': (18.0, 190.0),
    'portamento': (45.0, 430.0),
    'bow_change': (10.0, 125.0),
}


def _speed_name(value) -> str:
    if isinstance(value, str):
        s=value.strip().lower()
        return s if s in SPEED_QUANTILE else 'auto'
    x=float(value)
    if x <= 1.0: x *= 127.0
    if x < 21: return 'auto'
    if x < 63: return 'slow'
    if x < 106: return 'normal'
    return 'fast'


def speed_quantile(value) -> float:
    name=_speed_name(value)
    if name == 'auto': return 0.50
    return float(SPEED_QUANTILE[name])


def _art_family(articulation) -> str:
    if isinstance(articulation, str):
        s=articulation.strip().lower().replace(' ','_')
    else:
        i=int(articulation)
        s={1:'legato',2:'portamento'}.get(i,'legato')
    if 'porta' in s or 'slide' in s: return 'portamento'
    if 'bow_change' in s or 'rebow' in s: return 'bow_change'
    return 'legato'


@dataclass
class TimingCalibration:
    # nested: family -> instrument(str) -> speed -> beat_fraction
    beat_fraction: dict
    source_count: int = 0
    schema_version: int = 1

    @classmethod
    def default(cls):
        return cls({fam:{'all':dict(v)} for fam,v in DEFAULT_BEAT_PRIORS.items()}, 0, 1)

    @classmethod
    def load(cls, path: str | Path | None):
        if not path or not Path(path).exists(): return cls.default()
        d=json.loads(Path(path).read_text(encoding='utf-8'))
        return cls(d.get('beat_fraction',{}), int(d.get('source_count',0)), int(d.get('schema_version',1)))

    def save(self, path: str | Path):
        p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({'schema_version':self.schema_version,'source_count':self.source_count,
                                 'beat_fraction':self.beat_fraction},indent=2,sort_keys=True),encoding='utf-8')

    def beat_target(self, articulation, speed_profile='normal', instrument: int | str='all', transition_speed=.5) -> float:
        fam=_art_family(articulation); speed=_speed_name(speed_profile)
        if speed=='auto':
            # Auto is continuous: transition_speed 0 -> slow, .5 -> normal, 1 -> fast.
            x=max(0.0,min(1.0,float(transition_speed)))
            a=self._lookup(fam,instrument,'slow'); b=self._lookup(fam,instrument,'normal'); c=self._lookup(fam,instrument,'fast')
            if x<=.5:
                t=x/.5; return a+(b-a)*t
            t=(x-.5)/.5; return b+(c-b)*t
        base=self._lookup(fam,instrument,speed)
        # The regular transition knob becomes a small trim when a discrete speed profile is selected.
        trim=1.12 - .24*max(0.0,min(1.0,float(transition_speed)))
        return base*trim

    def _lookup(self,fam,instrument,speed):
        inst=str(instrument)
        table=self.beat_fraction.get(fam,{})
        row=table.get(inst) or table.get('all') or DEFAULT_BEAT_PRIORS[fam]
        return float(row.get(speed,DEFAULT_BEAT_PRIORS[fam][speed]))


def target_transition(bpm: float, articulation, transition_speed=.5, speed_profile='auto',
                      instrument: int | str='all', calibration: TimingCalibration | None=None) -> dict:
    cal=calibration or TimingCalibration.default(); fam=_art_family(articulation)
    bpm=max(24.0,min(240.0,float(bpm)))
    beats=cal.beat_target(fam,speed_profile,instrument,transition_speed)
    ms=beats*(60_000.0/bpm)
    lo,hi=PHYSICAL_MS_CLAMPS[fam]
    ms=max(lo,min(hi,ms))
    # Recompute beat fraction after the physical clamp so the model sees the actual target.
    beats=ms/(60_000.0/bpm)
    return {'family':fam,'speed_profile':_speed_name(speed_profile),'speed_quantile':speed_quantile(speed_profile),
            'transition_beats':beats,'transition_ms':ms,'bpm':bpm}


def beat_duration_ms(bpm: float) -> float:
    return 60_000.0/max(24.0,min(240.0,float(bpm)))
