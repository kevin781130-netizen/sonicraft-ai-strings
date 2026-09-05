"""SONICRAFT v5.1 selective MIDI repair merger.

Starts from D Original and replaces only channel events inside accepted problem windows with the
winning candidate's events. Conductor/meta data remains from D. Final audio is rendered again from
the merged MIDI, so local audition WAVs are never audio-spliced into the master.
"""
from __future__ import annotations
from pathlib import Path
import struct
from compile_midi_performance_v29 import parse_midi,_track_bytes,_meta,_write_vlq

def _raw(e):
    if e.status==0xFF:
        if not e.data:return b""
        return _meta(e.data[0],e.data[1:])
    if e.status in (0xF0,0xF7):
        return bytes([e.status])+_write_vlq(len(e.data))+e.data
    return bytes([e.status])+e.data

def _is_note_off(e):
    if e.status>=0xF0:return False
    hi=e.status&0xF0
    return hi==0x80 or (hi==0x90 and len(e.data)>=2 and e.data[1]==0)

def _is_cc(e):
    return e.status<0xF0 and (e.status&0xF0)==0xB0

def _is_keyswitch_on(e):
    return e.status<0xF0 and (e.status&0xF0)==0x90 and len(e.data)>=2 and e.data[1]>0 and 24<=e.data[0]<36

def _patch_event(e,start,end,pre):
    tick=int(e.tick)
    if start<=tick<end:return e.status<0xF0
    if tick==end:
        # Close notes / gesture state belonging to the selected phrase, but do not steal a
        # back-to-back next phrase's note-on or fresh CC state.
        return _is_note_off(e) or (_is_cc(e) and len(e.data)>=2 and e.data[0] in (38,39) and e.data[1] in (0,64))
    if max(0,start-pre)<=tick<start:
        # Compiler pre-roll: CC + keyswitch only. Never replace a previous phrase's musical note.
        return _is_cc(e) or _is_keyswitch_on(e)
    return False

def splice_midi_windows_v51(base_midi,candidate_midis,decisions,out_path,pre_control_ticks=14):
    base_midi=Path(base_midi);out_path=Path(out_path)
    fmt,division,btracks=parse_midi(base_midi)
    ctracks={}
    for slot,p in candidate_midis.items():
        f,d,tr=parse_midi(Path(p))
        if f!=fmt or d!=division or len(tr)!=len(btracks):
            raise ValueError(f"candidate {slot} MIDI topology mismatch")
        ctracks[slot]=tr

    # Non-overlap is a hard contract from Selective Phrase Search.
    ordered=sorted((dict(x) for x in decisions),key=lambda x:(int(x["start_tick"]),int(x["end_tick"])))
    for a,b in zip(ordered,ordered[1:]):
        if int(b["start_tick"])<=int(a["end_tick"]):
            raise ValueError("selective merge windows overlap")

    out_tracks=[]
    for ti,base in enumerate(btracks):
        if ti==0:
            chosen=list(base)
        else:
            # Meta/SysEx always comes from D. Only ordinary channel events are locally replaceable.
            chosen=[e for e in base]
            for w in ordered:
                slot=str(w["winner"]).upper()
                if slot=="D":continue
                if slot not in ctracks:raise ValueError(f"missing candidate slot {slot}")
                start=int(w["start_tick"]);end=int(w["end_tick"]);pre=int(pre_control_ticks)
                # Replace only the selected phrase's channel events. The end boundary is guarded
                # so a back-to-back unselected phrase beginning on the same tick stays D Original.
                chosen=[e for e in chosen if not _patch_event(e,start,end,pre)]
                chosen.extend(e for e in ctracks[slot][ti] if _patch_event(e,start,end,pre))

        raws=[]
        for e in chosen:
            if e.status==0xFF and e.data and e.data[0]==0x2F:continue
            r=_raw(e)
            if r:raws.append((int(e.tick),1 if e.status<0xF0 else 0,r))
        out_tracks.append(_track_bytes(raws))

    hdr=b"MThd"+struct.pack(">IHHH",6,fmt,len(out_tracks),division)
    out_path.write_bytes(hdr+b"".join(b"MTrk"+struct.pack(">I",len(tr))+tr for tr in out_tracks))
    return out_path
