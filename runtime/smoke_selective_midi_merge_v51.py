from pathlib import Path
import tempfile,struct
from compile_midi_performance_v29 import _track_bytes,_name_event,parse_midi
from compile_musicxml_strings_v41 import _tempo_meta,PPQ
from selective_midi_merge_v51 import splice_midi_windows_v51

def make(p,cc_mid):
    conductor=_track_bytes([(0,0,_name_event("merge")),(0,1,_tempo_meta(120.0))])
    ev=[(0,0,_name_event("Vln I")),
        (0,1,bytes([0xB0,22,64])),
        (0,2,bytes([0x90,69,90])),(PPQ,2,bytes([0x80,69,0])),
        (PPQ,1,bytes([0xB0,22,cc_mid])),
        (PPQ,2,bytes([0x90,72,90])),(2*PPQ,2,bytes([0x80,72,0])),
        (2*PPQ,1,bytes([0xB0,22,70])),
        (2*PPQ,2,bytes([0x90,74,90])),(3*PPQ,2,bytes([0x80,74,0]))]
    tracks=[conductor,_track_bytes(ev),
            _track_bytes([(0,0,_name_event("Vln II"))]),
            _track_bytes([(0,0,_name_event("Viola"))]),
            _track_bytes([(0,0,_name_event("Cello"))])]
    hdr=b"MThd"+struct.pack(">IHHH",6,1,5,PPQ)
    p.write_bytes(hdr+b"".join(b"MTrk"+struct.pack(">I",len(tr))+tr for tr in tracks))

with tempfile.TemporaryDirectory() as td:
    td=Path(td);d=td/"D.mid";a=td/"A.mid";b=td/"B.mid";c=td/"C.mid";o=td/"M.mid"
    make(d,80);make(a,90);make(b,100);make(c,110)
    splice_midi_windows_v51(d,{"A":a,"B":b,"C":c},
        [{"start_tick":PPQ,"end_tick":2*PPQ,"winner":"C"}],o)
    _,_,dt=parse_midi(d);_,_,ct=parse_midi(c);_,_,mt=parse_midi(o)
    def sig(tr,t0,t1):
        return [(e.tick,e.status,e.data) for e in tr[1] if e.status<0xF0 and t0<=e.tick<=t1]
    # Before the patch: identical to D.
    assert sig(mt,0,PPQ-1)==sig(dt,0,PPQ-1)
    # Core repair value comes from C.
    core=[e for e in mt[1] if e.status<0xF0 and e.tick==PPQ]
    assert any((e.status&0xF0)==0xB0 and e.data==bytes([22,110]) for e in core),core
    # Back-to-back next-phrase onset/CC at the exact end boundary remains D.
    boundary=[e for e in mt[1] if e.status<0xF0 and e.tick==2*PPQ]
    assert any((e.status&0xF0)==0xB0 and e.data==bytes([22,70]) for e in boundary),boundary
    assert any((e.status&0xF0)==0x90 and e.data==bytes([74,90]) for e in boundary),boundary
    # After patch: identical to D.
    assert sig(mt,2*PPQ+1,3*PPQ)==sig(dt,2*PPQ+1,3*PPQ)
    # Conductor track remains D exactly.
    assert [(e.tick,e.status,e.data) for e in mt[0]]==[(e.tick,e.status,e.data) for e in dt[0]]
print("SONICRAFT v5.1 selective MIDI merge boundary smoke OK")
