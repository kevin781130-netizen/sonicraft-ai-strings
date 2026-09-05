from pathlib import Path
import tempfile,struct
from compile_midi_performance_v29 import _track_bytes,_name_event
from compile_musicxml_strings_v41 import _tempo_meta,PPQ
from shadow_render_auto_v50 import start_shadow_service_v50,render_midi_v50

def make_long_midi(p):
    conductor=_track_bytes([(0,0,_name_event('v5.0 long chunk smoke')),(0,1,_tempo_meta(60.0))])
    # 50-second note at 60 BPM; add authored lane controls and gesture enable.
    ev=[(0,0,_name_event('Violin I')),
        (0,1,bytes([0xB0,22,80])),(0,1,bytes([0xB0,23,64])),(0,1,bytes([0xB0,38,100])),
        (0,2,bytes([0x90,69,100])),(50*PPQ,2,bytes([0x80,69,0])),(50*PPQ,3,bytes([0xB0,38,0]))]
    tracks=[conductor,_track_bytes(ev),_track_bytes([(0,0,_name_event('Vln II'))]),_track_bytes([(0,0,_name_event('Viola'))]),_track_bytes([(0,0,_name_event('Cello'))])]
    hdr=b'MThd'+struct.pack('>IHHH',6,1,len(tracks),PPQ)
    p.write_bytes(hdr+b''.join(b'MTrk'+struct.pack('>I',len(tr))+tr for tr in tracks))

with tempfile.TemporaryDirectory() as td:
    td=Path(td);m=td/'long.mid';make_long_midi(m);proc=None
    try:
        proc,_=start_shadow_service_v50(port=49552,mock=True,cache_dir=td/'cache')
        r=render_midi_v50(m,td/'long.wav',port=49552,sample_rate=8000,chunk_seconds=40.0,overlap_seconds=.75,tail_seconds=.5)
        assert r['frames']>50*8000 and r['chunks']>=2,r
        assert r['peak']>0 and (td/'long.wav').exists()
    finally:
        if proc is not None:proc.terminate();proc.wait(timeout=3)
print('SONICRAFT v5.0 >45s Shadow chunk/crossfade smoke OK',r['chunks'],r['frames'],round(r['peak'],6))
