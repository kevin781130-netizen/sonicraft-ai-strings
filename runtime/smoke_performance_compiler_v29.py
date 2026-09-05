from pathlib import Path
import struct,tempfile,json
from compile_midi_performance_v29 import compile_file,parse_midi,pair_notes,PARTS

def vlq(v):
    b=[v&127];v>>=7
    while v:b.append((v&127)|128);v>>=7
    return bytes(reversed(b))
def tr(events):
    o=bytearray();last=0
    for tick,raw in events:o+=vlq(tick-last)+raw;last=tick
    o+=b'\x00\xff\x2f\x00';return bytes(o)
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/'in.mid';events=[(0,b'\xff\x51\x03\x07\xa1\x20')]
    # chord -> should distribute, then melodic legato phrase
    for note,vel in [(48,90),(60,92),(67,96),(76,100)]:events.append((0,bytes([0x90,note,vel])))
    for note in (48,60,67,76):events.append((480,bytes([0x80,note,0])))
    events += [(480,bytes([0x90,76,90])),(960,bytes([0x80,76,0])),(940,bytes([0x90,78,92])),(1440,bytes([0x80,78,0]))]
    events.sort(key=lambda x:x[0]);t=tr(events);src.write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,480)+b'MTrk'+struct.pack('>I',len(t))+t)
    out,man,notes=compile_file(src);assert out.is_file() and man.is_file();d=json.loads(man.read_text());assert d['midi_authority_lock'] and len(d['notes'])==6
    _,div,tracks=parse_midi(out);assert len(tracks)==5 and div==480
    compiled=pair_notes(tracks);parts={n.channel for n in compiled if n.note>=36};assert {0,1,2,3}.issubset(parts)
    chord=[n for n in notes if n.start==0];assert len({n.part for n in chord})==4
    assert all(0<=n.cc1<=127 and 0<=n.cc3<=127 and 0<=n.articulation<12 for n in notes)
print('SONICRAFT v2.9 DAW-native Performance Compiler smoke OK')
