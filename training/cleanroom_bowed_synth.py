from __future__ import annotations
"""Independent SONICRAFT bowed-string physical teacher (training only).

This is NOT an implementation of, extraction from, or emulation of any proprietary
instrument. Public product manuals may define behavioral test targets, but all DSP,
parameterization and generated audio here are independently authored from general
bowed-string acoustics and permissive/open research references.
"""
from dataclasses import dataclass, asdict, replace
import math
import numpy as np

ARTICULATIONS = (
    "sustain","legato","portamento","expressive_long","marcato","staccato",
    "spiccato","tremolo","pizzicato","trill","harmonic","flautando"
)

RANGES = {
    0: (55, 96),  # Violin I
    1: (55, 93),  # Violin II
    2: (48, 84),  # Viola
    3: (36, 72),  # Cello
}
BODY_FORMANTS = {
    0: ((420,1.0,150),(960,.70,260),(2850,.45,700)),
    1: ((400,1.0,160),(900,.72,270),(2650,.44,720)),
    2: ((330,1.0,150),(760,.76,260),(2200,.46,650)),
    3: ((220,1.0,120),(520,.82,220),(1450,.54,520)),
}

@dataclass
class BowedControls:
    instrument: int
    articulation: int
    pitch: float
    velocity: float
    bow_speed: float
    bow_force: float
    contact_point: float      # 0=near bridge, 1=toward fingerboard
    vibrato_depth_cents: float
    vibrato_rate_hz: float
    friction_noise: float
    contact_notch_depth: float  # independent notch strength, 0=no notch / 1=deep contact-point minima
    bow_lift: float
    bow_direction: float      # -1 down, +1 up; hidden physical teacher value
    slide_semitones: float
    slide_time: float         # fraction of note
    tremolo_rate_hz: float
    player_dispersion: float
    section_players: int = 1
    section_pitch_spread_cents: float = 0.0
    section_timing_spread_ms: float = 0.0
    section_bow_spread: float = 0.0

    def manifest(self):
        d=asdict(self)
        # Expose an independent, generic physics-label space. These are SONICRAFT
        # labels derived from our own teacher equations, not proprietary parameters.
        force=float(np.clip(self.bow_force,0,1)); speed=float(np.clip(self.bow_speed,0,1))
        brightness=float(np.clip(.65 + .85*speed + .55*force - .45*(self.articulation==11), .55, 2.0))
        d["spectral_slope"] = float(np.clip(1.72 - .60*brightness, .62, 1.55))
        scratch=float(np.clip((force-.72)*3.0,0,1)*np.clip((speed-.55)*2.2,0,1))
        airy=float(np.clip((.26-force)*3.0,0,1))
        d["residual_energy"] = float(np.clip(self.friction_noise*(.35+.75*scratch)+.11*airy,0,.45))
        for k in ("bow_speed","bow_force","contact_point","vibrato_depth_cents","vibrato_rate_hz",
                  "friction_noise","spectral_slope","contact_notch_depth","residual_energy",
                  "section_pitch_spread_cents","section_timing_spread_ms","section_bow_spread"):
            d[k+"_known"]=1.0
        d.update({
            "training_origin":"modeled",
            "source_kind":"modeled",
            "cleanroom_spec_version":"SONICRAFT-BOWED-1.0",
            "articulation_name":ARTICULATIONS[self.articulation],
        })
        return d

def midi_hz(p): return 440.0 * (2.0 ** ((np.asarray(p)-69.0)/12.0))

def _smoothstep(x):
    x=np.clip(x,0,1); return x*x*(3-2*x)

def _envelope(t, art, bow_lift):
    n=len(t); end=max(float(t[-1]),1e-6)
    x=t/end
    attack=.025; release=.08
    if art in (4,): attack=.006
    if art in (5,): attack=.004; release=.42
    if art in (6,): attack=.002; release=.58
    if art==8: attack=.001; release=.78
    if art==11: attack=.055; release=.12
    a=_smoothstep(x/max(attack,1e-4))
    r=_smoothstep((1-x)/max(release,1e-4))
    env=a*r
    if art in (5,6,8):
        decay={5:5.0,6:7.0,8:4.2}[art]
        env*=np.exp(-decay*x)
    # bow_lift mainly changes release damping in this independent model.
    if bow_lift>.5:
        env*=np.where(x>.88,np.exp(-35*(x-.88)),1.0)
    if art==4: env*=1.0+0.18*np.exp(-70*x)
    return env.astype(np.float64)

def _body_gain(freq, instrument, dispersion):
    gain=np.ones_like(freq,dtype=np.float64)*.32
    shift=1.0 + dispersion*.025
    for fc,amp,bw in BODY_FORMANTS[instrument]:
        gain += amp*np.exp(-.5*((freq-fc*shift)/bw)**2)
    return gain

def synthesize(ctrl: BowedControls, seconds=2.0, sample_rate=48000, seed=0):
    rng=np.random.default_rng(seed); n=max(32,int(seconds*sample_rate)); t=np.arange(n,dtype=np.float64)/sample_rate
    x=t/max(seconds,1e-6)
    art=int(ctrl.articulation)

    pitch=np.full(n,float(ctrl.pitch),np.float64)
    if art==2 or abs(ctrl.slide_semitones)>.05:
        st=np.clip(ctrl.slide_time,.04,.92)
        u=_smoothstep(x/st)
        pitch=(ctrl.pitch-ctrl.slide_semitones)*(1-u)+ctrl.pitch*u
    if art==9:  # trill, alternate around target
        trill=(np.sin(2*np.pi*(6.2+1.2*ctrl.velocity)*t)>0).astype(float)
        pitch += 2.0*trill
    vib_depth=ctrl.vibrato_depth_cents
    if art in (5,6,8): vib_depth*=.20
    if vib_depth>0:
        onset=.10 if art in (0,1,2,3,11) else .02
        vg=_smoothstep((x-onset)/.16)
        # tiny low-rate player variation prevents clock-perfect vibrato.
        rate=ctrl.vibrato_rate_hz*(1+.025*np.sin(2*np.pi*.43*t+seed*.13))
        phase=2*np.pi*np.cumsum(rate)/sample_rate
        pitch += (vib_depth/100.0)*vg*np.sin(phase)
    f0=midi_hz(pitch)
    phase=2*np.pi*np.cumsum(f0)/sample_rate

    # Independent bowed-string source: harmonic slope, contact-point comb/notch,
    # instrument body resonances, and nonlinear friction-noise residual.
    force=np.clip(ctrl.bow_force,0,1); speed=np.clip(ctrl.bow_speed,0,1); cp=np.clip(ctrl.contact_point,0,1)
    brightness=np.clip(.65 + .85*speed + .55*force - .45*(art==11), .55, 2.0)
    alpha=np.clip(1.72 - .60*brightness, .62, 1.55)
    max_h=int(min(56,max(8,(sample_rate*.46)/max(float(np.median(f0)),20))))
    y=np.zeros(n,np.float64)
    # near bridge -> smaller physical beta -> broader bright spectrum; fingerboard -> larger beta.
    beta=.035 + .19*cp
    dispersion=float(ctrl.player_dispersion)
    for h in range(1,max_h+1):
        fh=h*f0
        # Bow/contact excitation minima. Keep a floor so this teacher is robust rather than idealized-zero.
        notch=np.clip(ctrl.contact_notch_depth,0,1)
        contact=(1.0-notch)+notch*np.abs(np.sin(np.pi*h*beta))
        amp=contact/(h**alpha)
        if art==10:  # natural-harmonic-like teacher: de-emphasize fundamental/odd partials
            amp*= (0.22 if h==1 else (1.35 if h%2==0 else .45))
        body=_body_gain(fh,ctrl.instrument,dispersion)
        y += amp*body*np.sin(h*phase + .13*h*ctrl.bow_direction)

    env=_envelope(t,art,ctrl.bow_lift)
    # Tremolo here is repeated bow-energy modulation, not pitch tremolo.
    if art==7:
        tr=.55+.45*(.5+.5*np.sin(2*np.pi*max(3.0,ctrl.tremolo_rate_hz)*t))
        env*=tr
    if art==8:  # pizzicato excitation spike / no sustained bow friction
        env*=1.25
        pick=rng.normal(0,1,n)*np.exp(-65*t)
        y=.94*y+.15*pick

    # Friction residual rises at excessive force/speed and has a softer airy lane at very low force.
    scratch=np.clip((force-.72)*3.0,0,1)*np.clip((speed-.55)*2.2,0,1)
    airy=np.clip((.26-force)*3.0,0,1)
    noise_amount=np.clip(ctrl.friction_noise*(.35+.75*scratch)+.11*airy,0,.45)
    noise=rng.normal(0,1,n)
    # simple differentiated noise for bow hair / scrape energy
    noise=np.concatenate([[0.0],np.diff(noise)])
    y=(1-noise_amount)*y + noise_amount*noise

    # attack transient follows force/speed but is independently parameterized.
    attack_noise=(.018+.10*scratch+.025*force)*rng.normal(0,1,n)*np.exp(-55*t)
    y=(y+attack_noise)*env
    # velocity/bow speed define amplitude while preserving dynamic relationships.
    gain=.10 + .50*np.clip(ctrl.velocity,0,1) + .22*speed
    y*=gain
    peak=np.max(np.abs(y))+1e-9
    if peak>.98: y*=.98/peak
    return y.astype(np.float32)

def synthesize_section(ctrl: BowedControls, seconds=2.0, sample_rate=48000, seed=0):
    """Independent multi-player bowed-section teacher.

    This is intentionally a physics-supervision generator, not a final timbre
    target.  Each virtual player receives deterministic micro-variation in
    pitch, onset, bow state and vibrato; their exact dispersion values are
    retained in the manifest for training-only supervision.
    """
    players=max(1,int(ctrl.section_players))
    if players==1:
        return synthesize(ctrl,seconds,sample_rate,seed)
    rng=np.random.default_rng(seed+7919)
    n=max(32,int(seconds*sample_rate)); mix=np.zeros(n,np.float64)
    for j in range(players):
        pitch_delta=float(rng.normal(0,max(0.0,ctrl.section_pitch_spread_cents)))/100.0
        onset_ms=float(rng.normal(0,max(0.0,ctrl.section_timing_spread_ms)))
        bow_delta=float(rng.normal(0,max(0.0,ctrl.section_bow_spread)))
        pj=replace(
            ctrl,
            pitch=float(ctrl.pitch+pitch_delta),
            bow_speed=float(np.clip(ctrl.bow_speed+.38*bow_delta,.03,.99)),
            bow_force=float(np.clip(ctrl.bow_force+.30*bow_delta,.03,.99)),
            contact_point=float(np.clip(ctrl.contact_point-.22*bow_delta,.01,.99)),
            vibrato_depth_cents=float(max(0.0,ctrl.vibrato_depth_cents*(1+rng.normal(0,.10)))),
            vibrato_rate_hz=float(max(2.8,ctrl.vibrato_rate_hz+rng.normal(0,.22))),
            player_dispersion=float(np.clip(ctrl.player_dispersion+rng.normal(0,.35),-1.5,1.5)),
            section_players=1,
        )
        y=synthesize(pj,seconds,sample_rate,seed+1009*j)
        shift=int(round(onset_ms*sample_rate/1000.0))
        if shift>0:
            y=np.pad(y,(shift,0))[:n]
        elif shift<0:
            k=min(n,-shift); y=np.pad(y[k:],(0,k))[:n]
        mix+=y.astype(np.float64)
    # Preserve section-growth without clipping becoming the dominant teacher.
    mix/=max(1.0,players**0.72)
    peak=np.max(np.abs(mix))+1e-9
    if peak>.98: mix*=.98/peak
    return mix.astype(np.float32)

def random_controls(rng: np.random.Generator, instrument=None, articulation=None):
    inst=int(rng.integers(0,4) if instrument is None else instrument)
    art=int(rng.integers(0,len(ARTICULATIONS)) if articulation is None else articulation)
    lo,hi=RANGES[inst]; pitch=float(rng.integers(lo,hi+1))
    force=float(rng.uniform(.12,.90)); speed=float(rng.uniform(.18,.96)); cp=float(rng.uniform(.03,.92))
    if art==11: force=float(rng.uniform(.05,.24)); cp=float(rng.uniform(.52,.95))
    if art==4: force=float(rng.uniform(.55,.94)); speed=float(rng.uniform(.55,.98))
    vib=float(rng.uniform(0,58 if art not in (5,6,8) else 15))
    return BowedControls(
        instrument=inst, articulation=art, pitch=pitch, velocity=float(rng.uniform(.35,1.0)),
        bow_speed=speed, bow_force=force, contact_point=cp,
        vibrato_depth_cents=vib, vibrato_rate_hz=float(rng.uniform(4.2,7.2)),
        friction_noise=float(rng.uniform(.03,.23)), contact_notch_depth=float(rng.uniform(.55,.96)),
        bow_lift=float(rng.integers(0,2)),
        bow_direction=float(-1 if rng.random()<.5 else 1),
        slide_semitones=float(rng.uniform(-5,5) if art==2 else 0.0),
        slide_time=float(rng.uniform(.14,.62)), tremolo_rate_hz=float(rng.uniform(6,13)),
        player_dispersion=float(rng.uniform(-1,1)),
    )
