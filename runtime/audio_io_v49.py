"""SONICRAFT v4.9 audio loading helpers.

Primary path uses soundfile (already part of the runtime dependency set). PCM WAV fallback uses
the Python standard library. No resampling is performed: A/B/C/D must share sample rate.
"""
from __future__ import annotations
from pathlib import Path
import wave
import numpy as np

def load_audio_v49(path):
    p=Path(path)
    try:
        import soundfile as sf
        x,sr=sf.read(str(p),always_2d=True,dtype="float32")
        return np.asarray(x,np.float32),int(sr)
    except Exception:
        pass
    with wave.open(str(p),"rb") as w:
        sr=w.getframerate();ch=w.getnchannels();sw=w.getsampwidth();n=w.getnframes();raw=w.readframes(n)
    if sw==2:
        a=np.frombuffer(raw,dtype="<i2").astype(np.float32)/32768.0
    elif sw==3:
        b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3)
        v=(b[:,0].astype(np.int32)|(b[:,1].astype(np.int32)<<8)|(b[:,2].astype(np.int32)<<16))
        v=np.where(v&0x800000,v|~0xFFFFFF,v)
        a=v.astype(np.float32)/8388608.0
    elif sw==4:
        a=np.frombuffer(raw,dtype="<i4").astype(np.float32)/2147483648.0
    else:
        raise ValueError(f"unsupported PCM width: {sw}")
    return a.reshape(-1,ch),int(sr)

def load_render_set_v49(paths):
    audios=[];sample_rate=None
    for p in paths:
        x,sr=load_audio_v49(p)
        if sample_rate is None:sample_rate=sr
        if sr!=sample_rate:raise ValueError("A/B/C/D sample rates must match")
        if not np.isfinite(x).all():raise ValueError(f"non-finite audio: {p}")
        audios.append(x)
    min_frames=min(len(x) for x in audios)
    max_frames=max(len(x) for x in audios)
    if min_frames<32:raise ValueError("render too short")
    if (max_frames-min_frames)>max(256,int(sample_rate*.050)):
        raise ValueError("A/B/C/D durations differ by more than 50 ms")
    return [x[:min_frames] for x in audios],sample_rate,min_frames
