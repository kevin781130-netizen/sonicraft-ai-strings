"""SONICRAFT v5.1 local-window Shadow renderer.

The service receives the full MIDI-derived event history, but renders only a context-expanded
problem window. This preserves pre-window controls/active-note state exactly like the v5.0 chunk
renderer. Audio Judge sees the unfaded core; saved local audition WAVs get a tiny edge fade only.
"""
from __future__ import annotations
from pathlib import Path
import wave
import numpy as np

from compile_midi_performance_v29 import parse_midi
from shadow_render_auto_v50 import (
    _tempo_points,_tick_to_seconds_fn,compiled_midi_to_shadow_events_v50,
    _render_request,render_policy_flags_v50,
)

DEFAULT_PREROLL=.85
DEFAULT_POSTROLL=.85
MAX_LOCAL_CONTEXT_SECONDS=28.0

def tick_window_to_samples_v51(midi_path,start_tick,end_tick,sample_rate):
    fmt,division,tracks=parse_midi(Path(midi_path))
    tempo=_tempo_points(tracks)
    to_sec=_tick_to_seconds_fn(division,tempo)
    a=int(round(to_sec(int(start_tick))*int(sample_rate)))
    b=int(round(to_sec(int(end_tick))*int(sample_rate)))
    return max(0,a),max(a+1,b)

def _write_wav(path,x,sr):
    path=Path(path)
    try:
        import soundfile as sf
        sf.write(str(path),np.asarray(x,np.float32),int(sr),subtype="FLOAT")
    except Exception:
        pcm=(np.clip(np.asarray(x,np.float32),-1,1)*32767).astype("<i2")
        with wave.open(str(path),"wb") as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(int(sr));w.writeframes(pcm.tobytes())

def _audition_fade(x,sr,ms=8.0):
    y=np.asarray(x,np.float32).copy()
    n=min(len(y)//3,max(1,int(float(sr)*float(ms)/1000.0)))
    if n>1:
        f=np.linspace(0,1,n,dtype=np.float32)
        y[:n]*=f[:,None];y[-n:]*=f[::-1,None]
    return y

def render_midi_window_v51(midi_path,start_tick,end_tick,out_wav=None,host="127.0.0.1",port=49337,
                           sample_rate=48000,preroll=DEFAULT_PREROLL,postroll=DEFAULT_POSTROLL,
                           request_id=510000,max_context_seconds=MAX_LOCAL_CONTEXT_SECONDS):
    midi_path=Path(midi_path)
    events,end_sample,bpm=compiled_midi_to_shadow_events_v50(midi_path,int(sample_rate),tail_seconds=1.5)
    core_start,core_end=tick_window_to_samples_v51(midi_path,start_tick,end_tick,int(sample_rate))
    core_end=min(core_end,end_sample)
    pre=max(0,int(round(float(preroll)*sample_rate)))
    post=max(0,int(round(float(postroll)*sample_rate)))
    render_start=max(0,core_start-pre)
    render_end=min(end_sample,core_end+post)
    if render_end<=render_start:raise ValueError("empty local render window")
    context_seconds=(render_end-render_start)/float(sample_rate)
    if context_seconds>float(max_context_seconds):
        raise ValueError(f"local context {context_seconds:.3f}s exceeds {max_context_seconds:.3f}s selective limit")
    x,rh=_render_request(events,render_start,render_end,int(sample_rate),bpm,host,port,int(request_id),
                         flags=render_policy_flags_v50(False))
    ia=max(0,core_start-render_start);ib=min(len(x),core_end-render_start)
    core=x[ia:ib].copy()
    if len(core)<32:raise ValueError("local Judge core is too short")
    if out_wav is not None:_write_wav(out_wav,_audition_fade(core,sample_rate),sample_rate)
    return {
        "audio":core,"events":events,"core_start_sample":core_start,"core_end_sample":core_end,
        "render_start_sample":render_start,"render_end_sample":render_end,"sample_rate":int(sample_rate),
        "frames":len(core),"context_frames":len(x),"context_seconds":context_seconds,
        "wav":Path(out_wav) if out_wav is not None else None,
        "peak":float(np.max(np.abs(core))) if core.size else 0.0,
        "service_status":int(rh.status),
    }
