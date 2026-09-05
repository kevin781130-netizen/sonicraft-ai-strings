"""SONICRAFT v3.0 Project Bridge / MIDI Performance Command Lane.

The bridge patches only SONICRAFT-reserved global command CCs. Musical note events,
keyswitches, authored CC lanes and arbitrary host MIDI remain untouched.

This gives Cubase/Studio One a DAW-native, region-scoped control surface for SONICRAFT's
performance intelligence without requiring a proprietary piano-roll editor.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse, hashlib, json, struct, sys

# MIDI CC 102..119 are undefined/reserved in the MIDI 1.0 controller table and are used
# exclusively as SONICRAFT host-command messages. Existing conventional CC mappings remain intact.
COMMAND_CCS = {
    'ai_assist': 102,
    'performance_style': 103,
    'smart_dynamics': 104,
    'smart_articulation': 105,
    'retake_target': 106,
    'retake_amount': 107,
    'retake_seed': 108,
    'midi_authority_lock': 109,
    'phrase_director': 110,
    'ensemble_looseness': 111,
    'auto_divisi': 112,
    'stage_perspective': 113,
    'independent_polyphony': 114,
    'ai_mix': 115,
    'ai_lookahead': 116,
    'layout_mode': 117,
    'single_instrument': 118,
    'humanize': 119,
}
COMMAND_CC_SET = set(COMMAND_CCS.values())

RETAKE_TARGETS = {
    'off': 0, 'timbre': 1, 'dynamics': 2, 'vibrato': 3, 'micro-pitch': 4,
    'micropitch': 4, 'timing': 5, 'timing-feel': 5, 'bow': 6, 'bow-attack': 6,
    'all': 7,
}
STYLES = {'neutral':0,'adagio':1,'allegro':2,'con-fuoco':3,'confuoco':3,'pop':4,'ballade':5}
ASSIST = {'manual':0,'assist':1,'auto':2}
STAGE = {'dry':0,'scoring':1,'wide':2,'room':3}

DEFAULTS = {
    'ai_assist': 1,
    'performance_style': 0,
    'smart_dynamics': 1,
    'smart_articulation': 1,
    'retake_target': 0,
    'retake_amount': 0.0,
    'retake_seed': 0,
    'midi_authority_lock': 1,
    'phrase_director': 1,
    'ensemble_looseness': 0.18,
    'auto_divisi': 0,
    'stage_perspective': 1,
    'independent_polyphony': 1,
    'ai_mix': 0.85,
    'ai_lookahead': 0.35,
    'layout_mode': 1,
    'single_instrument': 0,
    'humanize': 0.16,
}

@dataclass
class Event:
    tick: int
    status: int
    data: bytes
    order: int

class MidiError(ValueError): pass

def _read_vlq(data: bytes, pos: int):
    v=0
    for _ in range(4):
        if pos>=len(data): raise MidiError('truncated VLQ')
        b=data[pos]; pos+=1; v=(v<<7)|(b&0x7f)
        if not b&0x80: return v,pos
    raise MidiError('VLQ exceeds 4 bytes')

def _write_vlq(v: int) -> bytes:
    v=max(0,int(v)); out=[v&0x7f]; v>>=7
    while v: out.append((v&0x7f)|0x80); v>>=7
    return bytes(reversed(out))

def parse_midi(path: Path):
    raw=path.read_bytes()
    if len(raw)<14 or raw[:4]!=b'MThd': raise MidiError('not a Standard MIDI File')
    hlen=struct.unpack('>I',raw[4:8])[0]
    if hlen<6: raise MidiError('bad MThd')
    fmt,ntr,division=struct.unpack('>HHH',raw[8:14])
    if division&0x8000: raise MidiError('SMPTE division unsupported; export PPQ MIDI')
    pos=8+hlen; tracks=[]
    for ti in range(ntr):
        if raw[pos:pos+4]!=b'MTrk': raise MidiError(f'missing MTrk {ti}')
        ln=struct.unpack('>I',raw[pos+4:pos+8])[0]; tr=raw[pos+8:pos+8+ln]; pos+=8+ln
        tracks.append(_parse_track(tr))
    return fmt,division,tracks

def _parse_track(raw: bytes):
    pos=tick=order=0; running=None; out=[]
    while pos<len(raw):
        delta,pos=_read_vlq(raw,pos); tick+=delta
        if pos>=len(raw): break
        first=raw[pos]
        if first<0x80:
            if running is None: raise MidiError('running status without status')
            status=running
        else:
            status=first; pos+=1
            if status<0xF0: running=status
            elif status in (0xF0,0xF7,0xFF): running=None
        if status==0xFF:
            if pos>=len(raw): raise MidiError('truncated meta')
            typ=raw[pos]; pos+=1; ln,pos=_read_vlq(raw,pos); payload=raw[pos:pos+ln]; pos+=ln
            out.append(Event(tick,status,bytes([typ])+payload,order)); order+=1
            if typ==0x2F: break
        elif status in (0xF0,0xF7):
            ln,pos=_read_vlq(raw,pos); payload=raw[pos:pos+ln]; pos+=ln
            out.append(Event(tick,status,payload,order)); order+=1
        else:
            hi=status&0xF0; need=1 if hi in (0xC0,0xD0) else 2
            if first<0x80:
                payload=bytes([first])+raw[pos+1:pos+need]; pos+=need
            else:
                payload=raw[pos:pos+need]; pos+=need
            if len(payload)!=need: raise MidiError('truncated channel event')
            out.append(Event(tick,status,payload,order)); order+=1
    return out

def _event_bytes(e: Event) -> bytes:
    if e.status==0xFF:
        typ=e.data[0]; payload=e.data[1:]
        return b'\xff'+bytes([typ])+_write_vlq(len(payload))+payload
    if e.status in (0xF0,0xF7):
        return bytes([e.status])+_write_vlq(len(e.data))+e.data
    return bytes([e.status])+e.data

def write_midi(path: Path, fmt: int, division: int, tracks):
    blobs=[]
    for tr in tracks:
        # EOT is normalized to one final event. Stable order preserves all untouched same-tick events.
        ev=[e for e in tr if not (e.status==0xFF and e.data and e.data[0]==0x2F)]
        ev.sort(key=lambda e:(e.tick,e.order))
        buf=bytearray(); last=0
        for e in ev:
            t=max(last,int(e.tick)); buf += _write_vlq(t-last)+_event_bytes(e); last=t
        buf += b'\x00\xff\x2f\x00'
        blobs.append(bytes(buf))
    hdr=b'MThd'+struct.pack('>IHHH',6,int(fmt),len(blobs),int(division))
    path.write_bytes(hdr+b''.join(b'MTrk'+struct.pack('>I',len(b))+b for b in blobs))

def _norm_discrete(value: int, max_value: int) -> int:
    return int(round(max(0,min(max_value,int(value)))/max_value*127)) if max_value else 0

def encode_value(name: str, value) -> int:
    if name=='ai_assist': return _norm_discrete(int(value),2)
    if name=='performance_style': return _norm_discrete(int(value),5)
    if name=='retake_target': return _norm_discrete(int(value),7)
    if name=='stage_perspective': return _norm_discrete(int(value),3)
    if name=='layout_mode': return _norm_discrete(int(value),1)
    if name=='single_instrument': return _norm_discrete(int(value),3)
    if name=='retake_seed':
        # VST parameter is 8-bit internally while MIDI CC is 7-bit. Encode the requested
        # 0..255 nonce to the nearest representable CC value. The bridge records the effective
        # nonce after this quantization so a rendered take remains reproducible.
        return int(round(max(0,min(255,int(value)))/255*127))
    if name in ('smart_dynamics','smart_articulation','midi_authority_lock','phrase_director','auto_divisi','independent_polyphony'):
        return 127 if bool(value) else 0
    if name in ('retake_amount','ensemble_looseness','ai_mix','ai_lookahead','humanize'):
        return int(round(max(0.0,min(1.0,float(value)))*127))
    raise KeyError(name)

def decode_value(name: str, cc_value: int):
    v=max(0,min(127,int(cc_value)))
    if name=='ai_assist': return int(round(v/127*2))
    if name=='performance_style': return int(round(v/127*5))
    if name=='retake_target': return int(round(v/127*7))
    if name=='stage_perspective': return int(round(v/127*3))
    if name=='layout_mode': return int(round(v/127))
    if name=='single_instrument': return int(round(v/127*3))
    if name=='retake_seed': return int(round(v/127*255))
    if name in ('smart_dynamics','smart_articulation','midi_authority_lock','phrase_director','auto_divisi','independent_polyphony'):
        return v>=64
    return v/127.0

def command_name(cc: int):
    for k,v in COMMAND_CCS.items():
        if v==cc: return k
    return None

def _part_track_channels(tracks):
    """Return likely musical part tracks as (track_index, channel).

    v2.9/v3 compiled files are Tempo + 4 part tracks. For arbitrary MIDI, detect tracks with
    note-ons outside the SONICRAFT keyswitch bank. We cap at four parts.
    """
    found=[]
    for ti,tr in enumerate(tracks):
        counts={}
        for e in tr:
            if e.status<0xF0 and (e.status&0xF0)==0x90 and len(e.data)>=2 and e.data[1]>0 and not (24<=e.data[0]<=35):
                ch=e.status&0x0F; counts[ch]=counts.get(ch,0)+1
        if counts: found.append((ti,max(counts,key=counts.get)))
    if len(found)>=4: return found[:4]
    # Fallback for empty prepared part tracks.
    if len(tracks)>=5: return [(i,i-1) for i in range(1,5)]
    return found

def _latest_before(tr, channel: int, cc: int, tick: int, default: int) -> int:
    val=default
    for e in sorted(tr,key=lambda e:(e.tick,e.order)):
        if e.tick>=tick: break
        if e.status<0xF0 and (e.status&0xF0)==0xB0 and (e.status&0x0F)==channel and len(e.data)>=2 and e.data[0]==cc:
            val=e.data[1]
    return val

def _remove_command_range(tr, channel: int, start_tick: int, end_tick: int, ccs: set[int]):
    return [e for e in tr if not (start_tick<=e.tick<end_tick and e.status<0xF0 and (e.status&0xF0)==0xB0 and (e.status&0x0F)==channel and len(e.data)>=2 and e.data[0] in ccs)]

def apply_region(input_midi: Path, output_midi: Path, start_tick: int, end_tick: int, commands: dict,
                 bridge_json: Path|None=None, duplicate_parts: bool=True):
    if end_tick<=start_tick: raise MidiError('end must be after start')
    fmt,division,tracks=parse_midi(input_midi)
    part_tracks=_part_track_channels(tracks)
    if not part_tracks: raise MidiError('no musical tracks found')
    if not duplicate_parts: part_tracks=part_tracks[:1]
    encoded={name:encode_value(name,val) for name,val in commands.items()}
    target_ccs={COMMAND_CCS[k] for k in commands}
    # Region scope is transactional: set at start, restore pre-region value at end. Existing events
    # exactly at end win after the restore so authored later automation remains authoritative.
    for ti,ch in part_tracks:
        tr=tracks[ti]
        prior={cc:_latest_before(tr,ch,cc,start_tick,encode_value(command_name(cc),DEFAULTS[command_name(cc)])) for cc in target_ccs}
        kept=_remove_command_range(tr,ch,start_tick,end_tick,target_ccs)
        maxorder=max((e.order for e in kept),default=0)+1000
        for i,(name,val) in enumerate(encoded.items()):
            cc=COMMAND_CCS[name]
            kept.append(Event(start_tick,0xB0|ch,bytes([cc,val]),maxorder+i))
            # negative order makes restore happen before any existing authored automation at end.
            kept.append(Event(end_tick,0xB0|ch,bytes([cc,prior[cc]]),-1000+i))
        tracks[ti]=kept
    write_midi(output_midi,fmt,division,tracks)
    rec={
        'schema':1,'sonicraft_version':'3.0.0-host-intelligence-bridge',
        'source_midi':str(input_midi),'output_midi':str(output_midi),
        'division_ppq':division,'region':{'start_tick':start_tick,'end_tick':end_tick,'start_beat':start_tick/division,'end_beat':end_tick/division},
        'commands':commands,'encoded_cc':{k:{'cc':COMMAND_CCS[k],'value':v,'effective':decode_value(k,v)} for k,v in encoded.items()},
        'duplicated_to_part_tracks':bool(duplicate_parts),'part_tracks':[{'track':ti+1,'channel':ch+1} for ti,ch in part_tracks],
        'input_sha256':hashlib.sha256(input_midi.read_bytes()).hexdigest(),
        'output_sha256':hashlib.sha256(output_midi.read_bytes()).hexdigest(),
        'guarantee':'Only SONICRAFT command CCs in the requested region are replaced; note/key/other-CC data are preserved.',
    }
    if bridge_json:
        history=[]
        if bridge_json.exists():
            try:
                old=json.loads(bridge_json.read_text(encoding='utf-8')); history=list(old.get('history',[]))
            except Exception: history=[]
        history.append(rec)
        bridge_json.write_text(json.dumps({'schema':1,'sonicraft_version':rec['sonicraft_version'],'history':history[-128:]},ensure_ascii=False,indent=2),encoding='utf-8')
    return rec

def apply_snapshot(input_midi: Path, output_midi: Path, commands: dict|None=None, duplicate_parts: bool=True):
    """Inject a persistent v3 host-intelligence snapshot at tick 0 (no automatic reset)."""
    commands=dict(DEFAULTS if commands is None else commands)
    fmt,division,tracks=parse_midi(input_midi); part_tracks=_part_track_channels(tracks)
    if not duplicate_parts: part_tracks=part_tracks[:1]
    if not part_tracks: raise MidiError('no part tracks found')
    for ti,ch in part_tracks:
        tr=[e for e in tracks[ti] if not (e.tick==0 and e.status<0xF0 and (e.status&0xF0)==0xB0 and (e.status&0x0F)==ch and len(e.data)>=2 and e.data[0] in COMMAND_CC_SET)]
        base=min((e.order for e in tr),default=0)-1000
        for i,(name,value) in enumerate(commands.items()):
            tr.append(Event(0,0xB0|ch,bytes([COMMAND_CCS[name],encode_value(name,value)]),base+i))
        tracks[ti]=tr
    write_midi(output_midi,fmt,division,tracks)
    return division

def clear_region(input_midi: Path, output_midi: Path, start_tick: int, end_tick: int):
    fmt,division,tracks=parse_midi(input_midi); part_tracks=_part_track_channels(tracks)
    for ti,ch in part_tracks: tracks[ti]=_remove_command_range(tracks[ti],ch,start_tick,end_tick,COMMAND_CC_SET)
    write_midi(output_midi,fmt,division,tracks); return division

def _coerce_commands(a):
    c={}
    if a.assist is not None: c['ai_assist']=ASSIST[a.assist.lower()]
    if a.style is not None: c['performance_style']=STYLES[a.style.lower()]
    if a.smart_dynamics is not None: c['smart_dynamics']=a.smart_dynamics=='on'
    if a.smart_articulation is not None: c['smart_articulation']=a.smart_articulation=='on'
    if a.retake_target is not None: c['retake_target']=RETAKE_TARGETS[a.retake_target.lower()]
    if a.retake_amount is not None: c['retake_amount']=a.retake_amount
    if a.seed is not None: c['retake_seed']=a.seed
    if a.authority is not None: c['midi_authority_lock']=a.authority=='on'
    if a.phrase_director is not None: c['phrase_director']=a.phrase_director=='on'
    if a.looseness is not None: c['ensemble_looseness']=a.looseness
    if a.auto_divisi is not None: c['auto_divisi']=a.auto_divisi=='on'
    if a.stage is not None: c['stage_perspective']=STAGE[a.stage.lower()]
    if a.polyphony is not None: c['independent_polyphony']=a.polyphony=='on'
    if a.ai_mix is not None: c['ai_mix']=a.ai_mix
    if a.lookahead is not None: c['ai_lookahead']=a.lookahead
    if a.layout is not None: c['layout_mode']=1 if a.layout=='q4' else 0
    if a.single_instrument is not None: c['single_instrument']=a.single_instrument
    if a.humanize is not None: c['humanize']=a.humanize
    return c

def main(argv=None):
    ap=argparse.ArgumentParser(description='SONICRAFT v3.0 DAW-native Project Bridge')
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('apply',help='Apply region-scoped SONICRAFT performance commands and restore prior state at region end.')
    p.add_argument('midi',type=Path); p.add_argument('-o','--out',type=Path); p.add_argument('--bridge-json',type=Path)
    g=p.add_mutually_exclusive_group(required=True); g.add_argument('--start-beat',type=float); g.add_argument('--start-tick',type=int)
    h=p.add_mutually_exclusive_group(required=True); h.add_argument('--end-beat',type=float); h.add_argument('--end-tick',type=int)
    p.add_argument('--assist',choices=list(ASSIST)); p.add_argument('--style',choices=list(STYLES))
    p.add_argument('--smart-dynamics',choices=['on','off']); p.add_argument('--smart-articulation',choices=['on','off'])
    p.add_argument('--retake-target',choices=sorted(set(RETAKE_TARGETS))); p.add_argument('--retake-amount',type=float); p.add_argument('--seed',type=int,help='Requested deterministic retake nonce 0..255; MIDI stores nearest 7-bit representable value.')
    p.add_argument('--authority',choices=['on','off']); p.add_argument('--phrase-director',choices=['on','off']); p.add_argument('--looseness',type=float)
    p.add_argument('--auto-divisi',choices=['on','off']); p.add_argument('--stage',choices=list(STAGE)); p.add_argument('--polyphony',choices=['on','off'])
    p.add_argument('--ai-mix',type=float); p.add_argument('--lookahead',type=float); p.add_argument('--layout',choices=['single','q4']); p.add_argument('--single-instrument',type=int,choices=range(4)); p.add_argument('--humanize',type=float); p.add_argument('--single-command-track',action='store_true')
    s=sub.add_parser('snapshot',help='Inject persistent command snapshot at tick 0.')
    s.add_argument('midi',type=Path); s.add_argument('-o','--out',type=Path); s.add_argument('--single-command-track',action='store_true')
    c=sub.add_parser('clear',help='Remove SONICRAFT command CCs in a region without touching music data.')
    c.add_argument('midi',type=Path); c.add_argument('-o','--out',type=Path)
    g=c.add_mutually_exclusive_group(required=True); g.add_argument('--start-beat',type=float); g.add_argument('--start-tick',type=int)
    h=c.add_mutually_exclusive_group(required=True); h.add_argument('--end-beat',type=float); h.add_argument('--end-tick',type=int)
    a=ap.parse_args(argv)
    try:
        fmt,division,_=parse_midi(a.midi)
        out=a.out or a.midi.with_name(a.midi.stem+'_SCBRIDGE.mid')
        if a.cmd=='snapshot':
            apply_snapshot(a.midi,out,DEFAULTS,not a.single_command_track); print('SONICRAFT v3.0 snapshot OK:',out); return 0
        st=a.start_tick if a.start_tick is not None else int(round(a.start_beat*division)); en=a.end_tick if a.end_tick is not None else int(round(a.end_beat*division))
        if a.cmd=='clear': clear_region(a.midi,out,st,en); print('SONICRAFT v3.0 bridge clear OK:',out); return 0
        commands=_coerce_commands(a)
        if not commands: raise MidiError('no performance command specified')
        bj=a.bridge_json or out.with_suffix('.bridge.json')
        rec=apply_region(a.midi,out,st,en,commands,bj,not a.single_command_track)
        print('SONICRAFT v3.0 Project Bridge OK'); print('MIDI:',out); print('History:',bj); print('Region:',rec['region']); print('Commands:',commands); return 0
    except Exception as e:
        print('ERROR:',e,file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
