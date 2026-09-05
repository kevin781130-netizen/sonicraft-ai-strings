"""SONICRAFT v2.9 DAW-Native Performance Compiler.

Dependency-free Standard MIDI File parser/writer that compiles a normal MIDI performance into
four explicit Q4 parts while preserving note identity. It is deliberately a host-first workflow:
Cubase/Studio One remain the editor and source of truth; SONICRAFT only adds deterministic
performance suggestions that can be edited or deleted like normal MIDI data.

Outputs:
- Type-1 MIDI: Tempo + Vln I + Vln II + Viola + Cello
- .performance.json sidecar with note-level decisions and retake matrix metadata

No model weights or training data are needed.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import argparse,json,math,struct,sys

PARTS=('Vln I','Vln II','Viola','Cello')
PART_CENTERS=(76,67,60,48)
KS_BASE=24  # C0 in SONICRAFT convention
ART_NAMES=('Sustain','Legato','Portamento','Expressive Long','Marcato','Staccato','Spiccato','Tremolo','Pizzicato','Trill','Harmonic','Flautando')

@dataclass
class MidiEvent:
    tick:int; status:int; data:bytes; track:int=0; order:int=0

@dataclass
class Note:
    start:int; end:int; note:int; velocity:int; channel:int; track:int; order:int
    part:int=-1; articulation:int=0; cc1:int=80; cc3:int=64; phrase:int=0

class MidiError(ValueError): pass

def _read_vlq(data:bytes,pos:int):
    v=0
    for _ in range(4):
        if pos>=len(data): raise MidiError('truncated VLQ')
        b=data[pos];pos+=1;v=(v<<7)|(b&0x7f)
        if not (b&0x80): return v,pos
    raise MidiError('VLQ exceeds 4 bytes')

def _write_vlq(v:int)->bytes:
    v=max(0,int(v));buf=[v&0x7f];v>>=7
    while v: buf.append((v&0x7f)|0x80);v>>=7
    return bytes(reversed(buf))

def parse_midi(path:Path):
    b=path.read_bytes();pos=0
    if b[:4]!=b'MThd' or len(b)<14: raise MidiError('not a Standard MIDI File')
    n=struct.unpack('>I',b[4:8])[0]
    if n<6: raise MidiError('bad MThd')
    fmt,ntr,division=struct.unpack('>HHH',b[8:14]);pos=8+n
    if division&0x8000: raise MidiError('SMPTE time division is not supported; use PPQ MIDI')
    tracks=[]
    for ti in range(ntr):
        if b[pos:pos+4]!=b'MTrk': raise MidiError(f'missing MTrk {ti}')
        ln=struct.unpack('>I',b[pos+4:pos+8])[0];raw=b[pos+8:pos+8+ln];pos+=8+ln
        tracks.append(_parse_track(raw,ti))
    return fmt,division,tracks

def _parse_track(raw:bytes,ti:int):
    pos=0;tick=0;running=None;events=[];order=0
    while pos<len(raw):
        delta,pos=_read_vlq(raw,pos);tick+=delta
        if pos>=len(raw): break
        first=raw[pos]
        if first<0x80:
            if running is None: raise MidiError('running status without status byte')
            status=running
        else:
            status=first;pos+=1
            if status<0xF0: running=status
            elif status in (0xF0,0xF7,0xFF): running=None
        if status==0xFF:
            if pos>=len(raw): raise MidiError('truncated meta event')
            typ=raw[pos];pos+=1;ln,pos=_read_vlq(raw,pos);payload=raw[pos:pos+ln];pos+=ln
            events.append(MidiEvent(tick,0xFF,bytes([typ])+payload,ti,order));order+=1
            if typ==0x2F: break
        elif status in (0xF0,0xF7):
            ln,pos=_read_vlq(raw,pos);payload=raw[pos:pos+ln];pos+=ln
            events.append(MidiEvent(tick,status,payload,ti,order));order+=1
        else:
            hi=status&0xF0;need=1 if hi in (0xC0,0xD0) else 2
            if first<0x80:
                payload=bytes([first])+raw[pos+1:pos+need];pos+=need
            else:
                payload=raw[pos:pos+need];pos+=need
            if len(payload)!=need: raise MidiError('truncated channel event')
            events.append(MidiEvent(tick,status,payload,ti,order));order+=1
    return events

def pair_notes(tracks):
    active={}  # (track,ch,note)-> stack
    out=[];serial=0
    all_events=sorted((e for tr in tracks for e in tr),key=lambda e:(e.tick,e.track,e.order))
    last_tick=max((e.tick for e in all_events),default=0)
    for e in all_events:
        if e.status>=0xF0: continue
        hi=e.status&0xF0;ch=e.status&0x0F
        if hi==0x90 and e.data[1]>0:
            active.setdefault((e.track,ch,e.data[0]),[]).append((e.tick,e.data[1],serial));serial+=1
        elif hi==0x80 or (hi==0x90 and e.data[1]==0):
            key=(e.track,ch,e.data[0]);stack=active.get(key)
            if stack:
                st,vel,ordr=stack.pop(0);out.append(Note(st,max(st+1,e.tick),e.data[0],vel,ch,e.track,ordr))
    for (tr,ch,n),stack in active.items():
        for st,vel,ordr in stack: out.append(Note(st,max(st+1,last_tick),n,vel,ch,tr,ordr))
    out.sort(key=lambda x:(x.start,x.note,x.order));return out

def _range_penalty(part,note):
    # Soft ranges; never delete/transplant a note. The penalty only decides ownership.
    lo=(55,50,43,36);hi=(103,96,88,76)
    if note<lo[part]: return (lo[part]-note)*3
    if note>hi[part]: return (note-hi[part])*3
    return 0

def assign_smart_divisi(notes):
    active=[[] for _ in range(4)]
    # Process onset groups so vertical harmony distributes across parts rather than load-balancing randomly.
    by_tick={}
    for n in notes:by_tick.setdefault(n.start,[]).append(n)
    for tick in sorted(by_tick):
        for p in range(4): active[p]=[x for x in active[p] if x.end>tick]
        group=sorted(by_tick[tick],key=lambda n:(-n.note,n.order))
        used=set()
        for n in group:
            best=None
            for p in range(4):
                reg=abs(n.note-PART_CENTERS[p])
                occupancy=len(active[p])*8
                crossing=0
                # high notes prefer upper desks; low notes lower desks
                ideal=0 if n.note>=72 else (1 if n.note>=64 else (2 if n.note>=55 else 3))
                crossing=abs(p-ideal)*4
                chord=10 if p in used and len(group)<=4 else 0
                cost=reg+occupancy+crossing+chord+_range_penalty(p,n.note)
                if best is None or cost<best[0]:best=(cost,p)
            n.part=best[1];active[n.part].append(n);used.add(n.part)
    return notes

def analyze_phrases(notes,division):
    for p in range(4):
        ns=sorted((n for n in notes if n.part==p),key=lambda n:(n.start,n.note))
        phrase=0;prev=None;phrase_start=0;phrase_end=0
        groups=[];cur=[]
        for n in ns:
            if prev is None or (n.start-prev.end)/division>1.5:
                if cur:groups.append(cur)
                cur=[];phrase+=1
            n.phrase=phrase;cur.append(n);prev=n
        if cur:groups.append(cur)
        for g in groups:
            p0=min(n.start for n in g);p1=max(n.end for n in g);span=max(1,p1-p0)
            for i,n in enumerate(g):
                dur=(n.end-n.start)/division
                nxt=g[i+1] if i+1<len(g) else None
                prv=g[i-1] if i else None
                gap=((nxt.start-n.end)/division) if nxt else 99
                overlap=bool(nxt and nxt.start<=n.end+int(.08*division))
                # Existing 12-class vocabulary only: no fake untrained technique IDs.
                if dur<.22: art=6 if dur<.14 else 5
                elif overlap and gap<.12: art=1
                elif dur<.65 and (not nxt or gap>.12): art=4
                elif dur>1.5 and n.velocity<72: art=3
                else: art=0
                n.articulation=art
                pos=(n.start-p0)/span;arch=math.sin(math.pi*max(0,min(1,pos)))
                leap=abs((nxt.note-n.note) if nxt else 0)
                authored=n.velocity/127
                dyn=max(.05,min(.98,authored*.78+.16 + .08*arch + min(.06,leap/12*.04)))
                if nxt is None: dyn-=.04
                n.cc1=int(round(max(0,min(1,dyn))*127))
                # long-note vibrato intent; still just editable CC3.
                vib=.30 + min(.45,max(0,dur-.35)*.22) + .08*arch
                n.cc3=int(round(max(0,min(1,vib))*127))
    return notes

def _track_bytes(events):
    # events: (tick, priority, raw-with-status-or-meta)
    events=sorted(events,key=lambda x:(x[0],x[1]));out=bytearray();last=0
    for tick,_,raw in events:
        tick=max(last,int(tick));out+=_write_vlq(tick-last)+raw;last=tick
    out+=_write_vlq(0)+b'\xff\x2f\x00';return bytes(out)

def _meta(typ,payload):return b'\xff'+bytes([typ])+_write_vlq(len(payload))+payload

def _name_event(name):return _meta(0x03,name.encode('utf-8'))

def write_compiled(path:Path,division:int,source_tracks,notes,emit_cc=True,emit_keyswitch=True):
    tempo=[]
    # Preserve tempo/time-signature/key-signature markers from source, deduplicated.
    seen=set()
    for tr in source_tracks:
        for e in tr:
            if e.status==0xFF and e.data and e.data[0] in (0x51,0x58,0x59):
                key=(e.tick,e.data)
                if key not in seen:seen.add(key);tempo.append((e.tick,1,_meta(e.data[0],e.data[1:])))
    tempo.insert(0,(0,0,_name_event('SONICRAFT Tempo / Conductor')))
    tracks=[_track_bytes(tempo)]
    for p,name in enumerate(PARTS):
        ev=[(0,0,_name_event('SONICRAFT '+name))]
        last_art=None
        for n in sorted((x for x in notes if x.part==p),key=lambda x:(x.start,x.note,x.order)):
            if emit_keyswitch and n.articulation!=last_art:
                kt=max(0,n.start-max(1,division//96));ks=KS_BASE+n.articulation
                ev.append((kt,1,bytes([0x90|p,ks,1])));ev.append((n.start,1,bytes([0x80|p,ks,0])));last_art=n.articulation
            if emit_cc:
                ev.append((n.start,2,bytes([0xB0|p,1,n.cc1])))
                ev.append((n.start,2,bytes([0xB0|p,3,n.cc3])))
            ev.append((n.start,3,bytes([0x90|p,n.note,max(1,min(127,n.velocity))])))
            ev.append((n.end,0,bytes([0x80|p,n.note,0])))
        tracks.append(_track_bytes(ev))
    hdr=b'MThd'+struct.pack('>IHHH',6,1,len(tracks),division)
    body=b''.join(b'MTrk'+struct.pack('>I',len(t))+t for t in tracks)
    path.write_bytes(hdr+body)

def performance_manifest(source:Path,output:Path,division:int,notes,takes=8):
    data={'schema':1,'sonicraft_version':'2.9','source_midi':source.name,'compiled_midi':output.name,'ppq':division,
          'midi_authority_lock':True,'phrase_director':True,'smart_divisi':True,
          'parts':list(PARTS),'articulations':list(ART_NAMES),
          'retake_matrix':{'targets':['Timbre','Dynamics','Vibrato','Micro-Pitch','Timing Feel','Bow / Attack','All'],'seeds':list(range(max(1,min(32,takes))))},
          'notes':[]}
    for n in notes:
        data['notes'].append({'start_tick':n.start,'end_tick':n.end,'pitch':n.note,'velocity':n.velocity,'source_channel':n.channel+1,'source_track':n.track+1,'part':PARTS[n.part],'part_index':n.part,'articulation':ART_NAMES[n.articulation],'articulation_id':n.articulation,'cc1':n.cc1,'cc3':n.cc3,'phrase':n.phrase})
    return data

def compile_file(src:Path,out:Path|None=None,manifest:Path|None=None,emit_cc=True,emit_keyswitch=True,takes=8):
    _,division,tracks=parse_midi(src);notes=pair_notes(tracks)
    if not notes: raise MidiError('no note events found')
    assign_smart_divisi(notes);analyze_phrases(notes,division)
    out=out or src.with_name(src.stem+'_SONICRAFT_Q4.mid')
    manifest=manifest or out.with_suffix('.performance.json')
    write_compiled(out,division,tracks,notes,emit_cc,emit_keyswitch)
    manifest.write_text(json.dumps(performance_manifest(src,out,division,notes,takes),ensure_ascii=False,indent=2),encoding='utf-8')
    return out,manifest,notes

def main(argv=None):
    ap=argparse.ArgumentParser(description='Compile ordinary MIDI into editable SONICRAFT Q4 DAW-native performance MIDI.')
    ap.add_argument('midi',type=Path);ap.add_argument('-o','--out',type=Path);ap.add_argument('--manifest',type=Path);ap.add_argument('--no-cc',action='store_true');ap.add_argument('--no-keyswitch',action='store_true');ap.add_argument('--takes',type=int,default=8)
    a=ap.parse_args(argv)
    try:o,m,notes=compile_file(a.midi,a.out,a.manifest,not a.no_cc,not a.no_keyswitch,a.takes)
    except Exception as e:print(f'ERROR: {e}',file=sys.stderr);return 2
    counts=[sum(n.part==p for n in notes) for p in range(4)]
    print('SONICRAFT v2.9 performance compile OK');print('MIDI:',o);print('Manifest:',m);print('Notes:',len(notes),'parts=',dict(zip(PARTS,counts)))
    return 0
if __name__=='__main__':raise SystemExit(main())
