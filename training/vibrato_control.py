from __future__ import annotations
import math

# Four active depth layers plus straight/no-vibrato. The renderer interpolates continuously,
# so these are musically stable anchor points, not sample-layer switches.
CC3_ANCHORS = (0, 32, 64, 96, 127)
DEPTH_CENTS_ANCHORS = (0.0, 12.0, 28.0, 48.0, 72.0)  # peak deviation, not peak-to-peak
DEPTH_NAMES = ('straight', 'light', 'natural', 'deep', 'intense')


def _interp(x, xs, ys):
    x=float(x)
    if x<=xs[0]: return float(ys[0])
    if x>=xs[-1]: return float(ys[-1])
    for i in range(len(xs)-1):
        if xs[i] <= x <= xs[i+1]:
            t=(x-xs[i])/(xs[i+1]-xs[i])
            return float(ys[i] + t*(ys[i+1]-ys[i]))
    return float(ys[-1])


def cc3_to_depth_cents(cc3: float | int) -> float:
    x=float(cc3)
    if x<=1.0: x*=127.0
    return _interp(max(0.0,min(127.0,x)),CC3_ANCHORS,DEPTH_CENTS_ANCHORS)


def depth_cents_to_cc3(depth_cents: float) -> float:
    return _interp(max(0.0,min(90.0,float(depth_cents))),DEPTH_CENTS_ANCHORS,CC3_ANCHORS)/127.0


def depth_name(cc3: float | int) -> str:
    x=float(cc3)
    if x<=1.0: x*=127.0
    idx=min(range(len(CC3_ANCHORS)),key=lambda i:abs(CC3_ANCHORS[i]-x))
    return DEPTH_NAMES[idx]


def default_vibrato_rate_hz(cc3: float, pitch_midi: float=69.0, instrument: int=0, tempo_bpm: float=68.0,
                            speed_profile: float | int | str='auto') -> float:
    """Natural-rate prior. CC3 primarily controls depth, not speed.

    Tempo is weak context only: violinists do not phase-lock vibrato cycles to the metronome.
    """
    c=max(0.0,min(1.0,float(cc3)))
    instrument_offset={0:.12,1:-.05,2:-.22}.get(int(instrument),0.0)
    register=.10*max(-1.0,min(1.0,(float(pitch_midi)-64.0)/24.0))
    tempo=.12*max(-1.0,min(1.0,(float(tempo_bpm)-72.0)/36.0))
    # CC20/Expression-Map speed profile may request a slower/faster human vibrato rate,
    # but the cycles are never phase-locked to the song tempo.
    try:
        try:
            from tempo_conditioning import speed_profile_name
        except ImportError:
            from .tempo_conditioning import speed_profile_name
        prof=speed_profile_name(speed_profile)
    except Exception:
        prof='auto' 
    rate_offset={'auto':0.0,'slow':-.62,'normal':0.0,'fast':.68}.get(prof,0.0)
    return max(4.0,min(7.2,5.15 + .35*c + instrument_offset + register + tempo + rate_offset))


def default_vibrato_onset_ms(cc3: float, tempo_bpm: float=68.0, note_duration_beats: float=2.0) -> float:
    c=max(0.0,min(1.0,float(cc3)))
    if c < .03: return 1e6
    spb=60.0/max(24.0,min(240.0,float(tempo_bpm)))
    # Lyrical strings often let the note speak before vibrato blooms. Long notes wait longer.
    beat_delay=.18 + .12*max(0.0,min(1.0,(float(note_duration_beats)-1.0)/3.0))
    beat_delay *= 1.10 - .30*c
    return max(90.0,min(460.0,beat_delay*spb*1000.0))


def default_vibrato_jitter(cc3: float) -> float:
    c=max(0.0,min(1.0,float(cc3)))
    return .015 + .035*c
