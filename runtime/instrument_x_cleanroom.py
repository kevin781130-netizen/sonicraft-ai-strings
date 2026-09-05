"""Clean-room performance intelligence inspired only by public product behavior.

No Instrument X code, models, presets, binaries or rendered material are used here.
This module implements SONICRAFT-owned behavior for:
- predictive dynamics
- context-driven smart articulation
- deterministic targeted performance retakes
- performance-style macros
All written MIDI/explicit CC values remain authoritative in Manual mode.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, math
import numpy as np
from portable_rng_v27 import normal_array

STYLE_NAMES = ('neutral','adagio','allegro','con_fuoco','pop','ballade')
RETAKE_NONE=0; RETAKE_TIMBRE=1; RETAKE_DYNAMICS=2; RETAKE_VIBRATO=3; RETAKE_MICROPITCH=4; RETAKE_TIMING=5; RETAKE_BOW_ATTACK=6; RETAKE_ALL=7

@dataclass(frozen=True)
class PerformancePolicy:
    assist_level:int=1
    style:int=0
    smart_dynamics:bool=False
    smart_articulation:bool=False
    polyphony:bool=True
    retake_target:int=0
    retake_nonce:int=0
    retake_amount:float=0.0
    stage_perspective:int=1
    multi_out:bool=False
    midi_authority_lock:bool=True
    phrase_director:bool=True
    ensemble_looseness:float=.18


def decode_flags(flags:int)->PerformancePolicy:
    f=int(flags)
    return PerformancePolicy(
        assist_level=max(0,min(2,f & 0x3)),
        style=max(0,min(5,(f>>2)&0x7)),
        smart_dynamics=bool((f>>5)&1),
        smart_articulation=bool((f>>6)&1),
        polyphony=bool((f>>7)&1),
        retake_target=max(0,min(7,(f>>8)&0x7)),
        retake_nonce=(f>>11)&0xFF,
        stage_perspective=max(0,min(3,(f>>19)&0x3)),
        retake_amount=max(0.0,min(1.0,((f>>21)&0xF)/15.0)),
        multi_out=bool((f>>25)&1),
        midi_authority_lock=bool((f>>26)&1),
        phrase_director=bool((f>>27)&1),
        ensemble_looseness=max(0.0,min(1.0,((f>>28)&0xF)/15.0)),
    )


def _smooth(x, radius=8):
    x=np.asarray(x,np.float32)
    if radius<=0 or x.size<3:return x.copy()
    k=np.arange(-radius,radius+1,dtype=np.float32)
    w=np.exp(-0.5*(k/max(1.0,radius*.45))**2);w/=w.sum()
    # NumPy 'same' returns max(len(x),len(w)); short realtime windows therefore
    # used to expand when the kernel was longer than the signal. Full+center-crop
    # keeps the control contract length invariant and matches the native zero-pad path.
    full=np.convolve(x,w,mode='full')
    start=(len(w)-1)//2
    return full[start:start+len(x)].astype(np.float32)


def _style_shape(style:int, phrase, onset, note_progress, tempo_bpm:float):
    p=np.asarray(phrase,np.float32); o=np.asarray(onset,np.float32); n=np.asarray(note_progress,np.float32)
    # All values are small residual intentions, not gain automation.
    if style==1: # adagio
        return .05*np.sin(np.pi*p)+.04*np.sin(np.pi*n)-.02*o
    if style==2: # allegro
        return .025*o+.02*(1-n)-.01*np.sin(np.pi*p)
    if style==3: # con fuoco
        return .08*o+.055*np.sin(np.pi*n)+.035
    if style==4: # pop
        pulse=np.sin(2*np.pi*p*4.0)
        return .03*np.maximum(0,pulse)+.03*o
    if style==5: # ballade
        return .045*np.sin(np.pi*p)+.025*np.sin(np.pi*n)-.015*o
    return np.zeros_like(p)


def predictive_dynamics(dynamics, pitch, gate, onset, note_progress, phrase_position,
                        prev_interval, next_interval, tempo_bpm:float, policy:PerformancePolicy):
    """Return a timbre/dynamics intent curve while preserving the user's lane as anchor.

    Manual => bit-identical. Assist blends up to 35%; Auto up to 65%.
    """
    d=np.asarray(dynamics,np.float32)
    if policy.assist_level<=0 or not policy.smart_dynamics:return d.copy()
    p=np.asarray(pitch,np.float32);g=np.asarray(gate,np.float32);o=np.asarray(onset,np.float32)
    prog=np.asarray(note_progress,np.float32); phr=np.asarray(phrase_position,np.float32)
    pi=np.asarray(prev_interval,np.float32); ni=np.asarray(next_interval,np.float32)
    register=np.clip((p-48.0)/36.0,0,1)
    leap=np.clip((np.abs(pi)+np.abs(ni))/24.0,0,1)
    contour=.035*(register-.5)+.045*leap+.035*o+.025*np.sin(np.pi*prog)
    style=_style_shape(policy.style,phr,o,prog,tempo_bpm)
    target=np.clip(d+contour+style,0.02,.98)*g + d*(1-g)
    target=_smooth(target,6)
    mix=.35 if policy.assist_level==1 else .65
    return np.clip(d*(1-mix)+target*mix,0,1).astype(np.float32)


def phrase_director_curve(dynamics, attack, transition, vibrato_onset, phrase_position, note_progress, next_interval, gate, policy:PerformancePolicy):
    """Phrase-level performance shaping; anchored to authored lanes and fully bypassable."""
    d=np.asarray(dynamics,np.float32).copy(); at=np.asarray(attack,np.float32).copy(); tr=np.asarray(transition,np.float32).copy(); vo=np.asarray(vibrato_onset,np.float32).copy()
    if not policy.phrase_director or policy.assist_level<=0:return d,at,tr,vo
    phr=np.asarray(phrase_position,np.float32); prog=np.asarray(note_progress,np.float32); ni=np.asarray(next_interval,np.float32); g=np.asarray(gate,np.float32)
    strength=.35 if policy.assist_level==1 else .65
    arch=np.sin(np.pi*np.clip(phr,0,1))*g
    cadence=(prog>.72)&(np.abs(ni)<1e-4)&(g>0)
    leap=np.clip(np.abs(ni)/12.,0,1)*g
    d=np.clip(d + strength*(.035*arch+.018*leap-.025*cadence),0,1)
    at=np.clip(at + strength*(.045*leap-.025*cadence),0,1)
    tr=np.clip(tr + strength*(.035*leap+.055*cadence),0,1)
    vo=np.clip(vo + strength*(.07*arch+.035*cadence),0,1)
    return d.astype(np.float32),at.astype(np.float32),tr.astype(np.float32),vo.astype(np.float32)

def smart_articulation_curve(current_art, gate, onset, note_duration_beats, legato,
                             prev_interval, next_interval, tempo_bpm:float, policy:PerformancePolicy):
    """Contextual base-articulation suggestion using the existing 12-class vocabulary.

    No new embeddings are introduced. Manual returns the authored articulation unchanged.
    """
    art=np.asarray(current_art,np.int64).copy()
    if policy.assist_level<=0 or not policy.smart_articulation:return art
    g=np.asarray(gate,np.float32); dur=np.asarray(note_duration_beats,np.float32); leg=np.asarray(legato,np.float32)
    pi=np.asarray(prev_interval,np.float32); ni=np.asarray(next_interval,np.float32)
    # Only override sustain-like authored states. Explicit special techniques remain untouched.
    mutable=(art==0)|(art==1)|(art==3)
    fast=float(tempo_bpm)>=118.0
    short=(dur>0)&(dur<(.42 if fast else .32))
    medium=(dur>=.32)&(dur<.8)
    connected=(leg>.55)&(np.abs(pi)<=7)&(np.abs(ni)<=7)
    proposed=art.copy()
    proposed[mutable & short & (g>0)]=6 if fast else 5  # spiccato / staccato
    proposed[mutable & (~short) & connected & (g>0)]=1  # legato
    proposed[mutable & medium & (~connected) & (g>0)]=4 # marcato
    # Assist only changes obviously neutral sustain slots; Auto can also resolve generic Legato/Expr.
    if policy.assist_level==1:
        mask=(art==0)&mutable
    else: mask=mutable
    art[mask]=proposed[mask]
    return art.astype(np.int64)


def _noise_curve(n:int, key:str, scale:float, smooth:int=10):
    return _smooth(normal_array(key,n),smooth)*float(scale)


def apply_targeted_retake(curves:dict, fingerprint:str, part:int, policy:PerformancePolicy):
    """Create a deterministic alternate performance without changing written notes.

    Retakes touch hidden/assist dimensions only. Pitch-note identity and explicit MIDI pitch-bend
    are deliberately excluded to preserve SONICRAFT's stricter score authority.
    """
    if policy.retake_target==RETAKE_NONE or policy.retake_amount<=0:return curves
    out={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in curves.items()}
    n=len(np.asarray(out.get('dynamics',[])))
    if n<=0:return out
    # v2.7 portable contract intentionally excludes model/backend fingerprint.
    base=f'retake-v28|p={part}|n={policy.retake_nonce}|t={policy.retake_target}|salt='
    a=float(policy.retake_amount)
    if policy.retake_target in (RETAKE_TIMBRE,RETAKE_ALL):
        # Timbre drift is expressed through hidden bow/attack/tightness, never note pitch.
        dr=_noise_curve(n,base+'11',.055*a,18)
        for k,scale in [('attack_character',.8),('short_tightness',.55),('bow_change_prob',.45)]:
            if k in out: out[k]=np.clip(np.asarray(out[k],np.float32)+dr*scale,0,1)
    if policy.retake_target in (RETAKE_DYNAMICS,RETAKE_ALL):
        dr=_noise_curve(n,base+'23',.045*a,24)
        if 'dynamics' in out: out['dynamics']=np.clip(np.asarray(out['dynamics'],np.float32)+dr,0,1)
    if policy.retake_target in (RETAKE_VIBRATO,RETAKE_ALL):
        dr=_noise_curve(n,base+'37',.10*a,16)
        if 'vibrato_onset' in out: out['vibrato_onset']=np.clip(np.asarray(out['vibrato_onset'],np.float32)+dr*.22,0,1)
        if 'vibrato_jitter' in out: out['vibrato_jitter']=np.clip(np.asarray(out['vibrato_jitter'],np.float32)+np.abs(dr)*.16,0,1)
    if policy.retake_target in (RETAKE_MICROPITCH,RETAKE_ALL) and not policy.midi_authority_lock:
        dr=_noise_curve(n,base+'41',.012*a,20)
        if 'pitchbend' in out: out['pitchbend']=np.clip(np.asarray(out['pitchbend'],np.float32)+dr,0,1)
    if policy.retake_target in (RETAKE_TIMING,RETAKE_ALL):
        dr=_noise_curve(n,base+'53',.06*a,12)
        if 'transition_speed' in out: out['transition_speed']=np.clip(np.asarray(out['transition_speed'],np.float32)+dr,0,1)
        if 'timing_feel' in out: out['timing_feel']=np.clip(np.asarray(out['timing_feel'],np.float32)+dr*.5,-1,1)
    if policy.retake_target in (RETAKE_BOW_ATTACK,RETAKE_ALL):
        dr=_noise_curve(n,base+'67',.075*a,10)
        if 'attack_character' in out: out['attack_character']=np.clip(np.asarray(out['attack_character'],np.float32)+dr,0,1)
        if 'bow_change_prob' in out: out['bow_change_prob']=np.clip(np.asarray(out['bow_change_prob'],np.float32)+dr*.7,0,1)
    return out


def articulation_stack_modifiers(art_curve, dynamics, attack, tightness, transition, policy:PerformancePolicy, expression_stack=None):
    """Physical residual layer over the existing 12 trained string articulations.

    v4.1 keeps the neural articulation ID in the original 0..11 vocabulary. A four-bit
    note-level stack (Accent/Legato/Tenuto/Expressive) changes only already-supported
    performance controls; it never invents an untrained acoustic technique.
    """
    a=np.asarray(art_curve,np.int64); d=np.asarray(dynamics,np.float32).copy()
    at=np.asarray(attack,np.float32).copy(); ti=np.asarray(tightness,np.float32).copy(); tr=np.asarray(transition,np.float32).copy()
    trem=a==7; leg=a==1; marc=a==4
    if np.any(trem):
        at[trem]=np.clip(at[trem]+.12,0,1); d[trem]=np.clip(d[trem]+.035,0,1)
    if np.any(leg):
        tr[leg]=np.clip(tr[leg]-.06,0,1); d[leg]=np.clip(d[leg]+.02,0,1)
    if np.any(marc):
        at[marc]=np.clip(at[marc]+.15,0,1); ti[marc]=np.clip(ti[marc]+.10,0,1)
    if expression_stack is not None:
        st=np.asarray(expression_stack,np.uint8)
        accent=(st&1)!=0; legato=(st&2)!=0; tenuto=(st&4)!=0; expressive=(st&8)!=0
        if np.any(accent):
            at[accent]=np.clip(at[accent]+.18,0,1);ti[accent]=np.clip(ti[accent]+.08,0,1);d[accent]=np.clip(d[accent]+.035,0,1)
        if np.any(legato):
            tr[legato]=np.clip(tr[legato]-.10,0,1);d[legato]=np.clip(d[legato]+.01,0,1)
        if np.any(tenuto):
            ti[tenuto]=np.clip(ti[tenuto]-.16,0,1);tr[tenuto]=np.clip(tr[tenuto]-.04,0,1)
        if np.any(expressive):
            at[expressive]=np.clip(at[expressive]-.10,0,1);d[expressive]=np.clip(d[expressive]+.04,0,1)
    return d,at,ti,tr
