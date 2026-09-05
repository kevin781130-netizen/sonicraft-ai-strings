from pathlib import Path
import tempfile,struct
import numpy as np
from compile_midi_performance_v29 import _track_bytes,_name_event
from compile_musicxml_strings_v41 import _tempo_meta,PPQ
from shadow_render_auto_v50 import start_shadow_service_v50,render_midi_v50
from shadow_render_selective_v51 import render_midi_window_v51,tick_window_to_samples_v51
from audio_io_v49 import load_audio_v49

def make_midi(p):
    conductor=_track_bytes([(0,0,_name_event("v5.1 selective render")),(0,1,_tempo_meta(60.0))])
    ev=[(0,0,_name_event("Vln I")),
        (0,1,bytes([0xB0,22,92])),(0,1,bytes([0xB0,23,70])),(0,1,bytes([0xB0,31,74])),
        (0,1,bytes([0xB0,38,96]))]
    for i,n in enumerate([69,71,72,74,76,77,79,81]):
        st=i*PPQ;en=(i+1)*PPQ
        ev.append((st,2,bytes([0x90,n,96])))
        ev.append((en,2,bytes([0x80,n,0])))
    ev.append((8*PPQ,3,bytes([0xB0,38,0])))
    tracks=[conductor,_track_bytes(ev),
            _track_bytes([(0,0,_name_event("Vln II"))]),
            _track_bytes([(0,0,_name_event("Viola"))]),
            _track_bytes([(0,0,_name_event("Cello"))])]
    hdr=b"MThd"+struct.pack(">IHHH",6,1,len(tracks),PPQ)
    p.write_bytes(hdr+b"".join(b"MTrk"+struct.pack(">I",len(tr))+tr for tr in tracks))

with tempfile.TemporaryDirectory() as td:
    td=Path(td);m=td/"sel.mid";make_midi(m);proc=None
    try:
        proc,_=start_shadow_service_v50(port=49561,mock=True,cache_dir=td/"cache")
        full=render_midi_v50(m,td/"full.wav",port=49561,sample_rate=8000,chunk_seconds=20,overlap_seconds=.5,tail_seconds=.25,request_seed=61000)
        local=render_midi_window_v51(m,3*PPQ,5*PPQ,td/"local.wav",port=49561,sample_rate=8000,
                                     preroll=.6,postroll=.6,request_id=61100)
        fx,fs=load_audio_v49(td/"full.wav")
        a,b=tick_window_to_samples_v51(m,3*PPQ,5*PPQ,8000)
        ref=fx[a:b,:2]
        n=min(len(ref),len(local["audio"]))
        assert n>15000,(n,a,b)
        # Mock service is project-sample deterministic; local full-history request should match
        # the same region of a whole render nearly exactly.
        err=float(np.max(np.abs(ref[:n]-local["audio"][:n])))
        assert err<2e-5,err
        assert local["context_frames"]>local["frames"]
        assert local["peak"]>0
    finally:
        if proc is not None:
            proc.terminate();proc.wait(timeout=3)
print("SONICRAFT v5.1 local Shadow context equivalence smoke OK",n,round(err,8))
