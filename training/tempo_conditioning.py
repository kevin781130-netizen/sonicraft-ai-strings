from __future__ import annotations
from performance_timing import TimingCalibration, target_transition, speed_quantile

ARTICULATION_NAMES = {
    0:'sustain',1:'legato',2:'portamento',3:'expressive_long',4:'marcato',5:'staccato',
    6:'spiccato',7:'tremolo',8:'pizzicato',9:'trill',10:'harmonic',11:'flautando'
}
SPEED_PROFILE_CC20={'auto':0,'slow':42,'normal':84,'fast':127}


def speed_profile_name(value) -> str:
    if isinstance(value,str):
        v=value.strip().lower();return v if v in SPEED_PROFILE_CC20 else 'auto'
    x=float(value)
    if x<=1.0:x*=127.0
    if x<21:return 'auto'
    if x<63:return 'slow'
    if x<106:return 'normal'
    return 'fast'


def speed_profile_norm(value) -> float:
    return {'auto':0.0,'slow':1/3,'normal':2/3,'fast':1.0}[speed_profile_name(value)]


def transition_target_ms(bpm: float, articulation: int|str, transition_speed: float=.5,
                         speed_profile: float|int|str='auto', instrument: int|str='all',
                         calibration: TimingCalibration|None=None) -> float:
    art=ARTICULATION_NAMES.get(int(articulation),'sustain') if not isinstance(articulation,str) else articulation
    # Sustain/other long articulations use legato family timing as a conservative connected-note prior.
    return target_transition(bpm,art,transition_speed,speed_profile,instrument,calibration)['transition_ms']


def tempo_features(bpm: float, note_duration_beats: float, articulation: int|str,
                   transition_speed: float=.5, speed_profile: float|int|str='auto',
                   instrument: int|str='all', calibration: TimingCalibration|None=None) -> dict:
    bpm=max(24.0,min(240.0,float(bpm)))
    art=ARTICULATION_NAMES.get(int(articulation),'sustain') if not isinstance(articulation,str) else articulation
    t=target_transition(bpm,art,transition_speed,speed_profile,instrument,calibration)
    return {
        'tempo_bpm':bpm,'seconds_per_beat':60.0/bpm,'note_duration_beats':max(0.0,float(note_duration_beats)),
        'transition_target_ms':t['transition_ms'],'transition_beats':t['transition_beats'],
        'speed_profile':speed_profile_norm(speed_profile),'speed_quantile':speed_quantile(speed_profile),
    }
