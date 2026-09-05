from pathlib import Path
import tempfile,struct,json
from compile_midi_performance_v30 import compile_file
from project_bridge_v30 import parse_midi,apply_region,clear_region,COMMAND_CCS,COMMAND_CC_SET

def vlq(v):
    b=[v&127];v>>=7
    while v:b.append((v&127)|128);v>>=7
    return bytes(reversed(b))
def tr(events):
    o=bytearray();last=0
    for tick,raw in sorted(events,key=lambda x:x[0]):o+=vlq(tick-last)+raw;last=tick
    o+=b'\x00\xff\x2f\x00';return bytes(o)
def musical_signature(path):
    _,_,tracks=parse_midi(path); sig=[]
    for ti,trk in enumerate(tracks):
        for e in trk:
            if e.status<0xF0 and (e.status&0xF0)==0xB0 and e.data[0] in COMMAND_CC_SET: continue
            if e.status==0xFF and e.data and e.data[0]==0x2F: continue
            sig.append((ti,e.tick,e.status,e.data))
    return sig

def command_events(path):
    _,_,tracks=parse_midi(path); out=[]
    for ti,trk in enumerate(tracks):
        for e in trk:
            if e.status<0xF0 and (e.status&0xF0)==0xB0 and e.data[0] in COMMAND_CC_SET: out.append((ti,e.tick,e.status&15,e.data[0],e.data[1]))
    return out

with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/'src.mid';ev=[(0,b'\xff\x51\x03\x07\xa1\x20')]
    for n in (48,60,67,76): ev.append((0,bytes([0x90,n,92])))
    for n in (48,60,67,76): ev.append((480,bytes([0x80,n,0])))
    ev += [(480,bytes([0x90,76,88])),(960,bytes([0x80,76,0]))]
    t=tr(ev);src.write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,480)+b'MTrk'+struct.pack('>I',len(t))+t)
    base,man,notes=compile_file(src)
    d=json.loads(man.read_text()); assert d['schema']==2 and d['host_command_lane']['cc_map']['retake_target']==106 and all('note_id' in n for n in d['notes'])
    base_cmd=command_events(base); assert any(t==0 and cc==COMMAND_CCS['layout_mode'] and v==127 for _,t,_,cc,v in base_cmd)
    # Add a completely unrelated authored CC74 event to prove the bridge is non-destructive.
    fmt,div,tracks=parse_midi(base)
    from project_bridge_v30 import Event,write_midi
    tracks[1].append(Event(300,0xB0,bytes([74,99]),99999))
    # An authored SONICRAFT command exactly at the region end must survive and win after restore.
    tracks[1].append(Event(720,0xB0,bytes([COMMAND_CCS['retake_target'],127]),100000)); authored=td/'authored.mid';write_midi(authored,fmt,div,tracks)
    sig0=musical_signature(authored)
    out=td/'retake.mid';hist=td/'retake.bridge.json'
    apply_region(authored,out,240,720,{'retake_target':2,'retake_amount':.75,'retake_seed':17,'phrase_director':True},hist)
    assert musical_signature(out)==sig0, 'bridge touched musical/authored MIDI data'
    ce=command_events(out); assert any(t==240 and cc==COMMAND_CCS['retake_target'] for _,t,_,cc,_ in ce); assert any(t==720 and cc==COMMAND_CCS['retake_target'] for _,t,_,cc,_ in ce)
    assert any(t==720 and cc==COMMAND_CCS['retake_target'] and v==127 for _,t,_,cc,v in ce), 'end-boundary authored command was destroyed'
    # Deterministic patching: identical input + command = byte-identical output.
    out2=td/'retake2.mid';apply_region(authored,out2,240,720,{'retake_target':2,'retake_amount':.75,'retake_seed':17,'phrase_director':True},None)
    assert out.read_bytes()==out2.read_bytes()
    # Clear only command lane within region; musical data still identical.
    cleared=td/'cleared.mid';clear_region(out,cleared,240,720); assert musical_signature(cleared)==sig0
    assert json.loads(hist.read_text())['history'][-1]['commands']['retake_target']==2
print('SONICRAFT v3.0 Project Bridge smoke OK')
