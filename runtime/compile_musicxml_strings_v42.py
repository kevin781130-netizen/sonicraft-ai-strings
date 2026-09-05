"""SONICRAFT v4.2 Strings Physical Performance Compiler.

MusicXML/XML/MXL -> semantic Score Graph -> 4x4 String Voice Bus -> physical-performance MIDI.
No new acoustic articulation classes are invented. Physical decisions remain ordinary editable CCs.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,struct,sys
from score_expression_graph_v40 import parse_score,graph_dict,PARTS,PPQ
from compile_musicxml_strings_v41 import allocate_voice_lanes,VOICE_CHANNELS,_cc,_stack_cc,_tempo_meta,_time_meta,_key_meta,KS_BASE
from compile_midi_performance_v29 import _track_bytes,_name_event
from string_physical_graph_v42 import plan_string_physics,physical_note_dict

PHYS_CC={
    "string_index":27,
    "position":28,
    "bow_direction":29,
    "bow_change":30,
    "bow_pressure":31,
    "contact_point":33,
    "portamento_route":34,
    "divisi_desk":35,
}

def _phys_cc_values(n):
    maxpos=8.0
    return {
        27:_cc((max(0,min(3,n.string_index))/3.0)*127.0),
        28:_cc((max(0,min(8,n.position_index))/maxpos)*127.0),
        29:127 if int(n.bow_direction)==1 else 0,
        30:127 if n.bow_change else 0,
        31:_cc(float(n.bow_pressure)*127.0),
        33:_cc(float(n.contact_point)*127.0),
        34:_cc(float(n.portamento_route)*127.0),
        35:_cc((max(0,min(3,n.divisi_desk))/3.0)*127.0),
    }

def write_midi(g,out:Path):
    conductor=[(0,0,_name_event("SONICRAFT v4.2 Strings Physical Conductor"))]
    conductor += [(x["tick"],1,_tempo_meta(x["bpm"])) for x in g.tempos]
    conductor += [(x["tick"],1,_time_meta(x["numerator"],x["denominator"])) for x in g.time_signatures]
    conductor += [(x["tick"],1,_key_meta(x["fifths"])) for x in g.key_signatures]
    tracks=[_track_bytes(conductor)]
    global_cmd=[(0,0,bytes([0xB0,117,127])),(0,0,bytes([0xB0,112,0])),
                (0,0,bytes([0xB0,114,127])),(0,0,bytes([0xB0,109,127])),(0,0,bytes([0xB0,110,127]))]
    for p,name in enumerate(PARTS):
        ev=[(0,0,_name_event("SONICRAFT "+name+" · v4.2 Physical String Voice Bus"))]
        if p==0:ev+=global_cmd
        for n in sorted((x for x in g.notes if x.part==p),key=lambda x:(x.start_tick,x.lane_channel,x.pitch)):
            ch=n.lane_channel
            pre=max(0,n.start_tick-max(1,PPQ//96))
            ev.append((pre,1,bytes([0x90|ch,KS_BASE+n.base_art,1])))
            ev.append((n.start_tick,0,bytes([0x80|ch,KS_BASE+n.base_art,0])))
            ev.append((pre,2,bytes([0xB0|ch,21,_stack_cc(n.stack)])))
            ev.append((pre,2,bytes([0xB0|ch,22,_cc(n.cc1)])))
            ev.append((pre,2,bytes([0xB0|ch,23,_cc(n.cc3)])))
            transition=64-(12 if n.stack&2 else 0)-(5 if n.stack&4 else 0)-int(round(n.portamento_route*18))
            attack=48+(22 if n.stack&1 else 0)-(12 if n.stack&8 else 0)
            if "down-bow" in n.technical:attack+=5
            if "up-bow" in n.technical:attack-=3
            attack += int(round((n.bow_pressure-.5)*16+(n.contact_point-.5)*12))
            tight=64+(10 if n.stack&1 else 0)-(20 if n.stack&4 else 0)+int(round((n.contact_point-.5)*12))
            ev.append((pre,2,bytes([0xB0|ch,24,_cc(transition)])))
            ev.append((pre,2,bytes([0xB0|ch,25,_cc(attack)])))
            ev.append((pre,2,bytes([0xB0|ch,26,_cc(tight)])))
            for cc,val in _phys_cc_values(n).items():
                ev.append((pre,2,bytes([0xB0|ch,cc,val])))
            ev.append((n.start_tick,3,bytes([0x90|ch,n.pitch,max(1,min(127,n.velocity))])))
            ev.append((n.end_tick,0,bytes([0x80|ch,n.pitch,0])))
        tracks.append(_track_bytes(ev))
    hdr=b"MThd"+struct.pack(">IHHH",6,1,len(tracks),PPQ)
    out.write_bytes(hdr+b"".join(b"MTrk"+struct.pack(">I",len(tr))+tr for tr in tracks))

def compile_file(src:Path,out:Path|None=None,score_json:Path|None=None):
    g=allocate_voice_lanes(parse_score(src))
    plan_string_physics(g)
    out=out or src.with_name(src.stem+"_SONICRAFT_STRINGS_v42.mid")
    score_json=score_json or out.with_suffix(".score.json")
    write_midi(g,out)
    data=graph_dict(g)
    data.update({
        "sonicraft_version":"4.2",
        "compiled_midi":out.name,
        "physical_performance_graph":{
            "planner":"deterministic ergonomic string/bow rules",
            "acoustic_claim":"control residual only; no new trained string-position timbre",
            "cc":{str(v):k for k,v in PHYS_CC.items()},
            "open_string":"derived from chosen string + finger_semitone == 0",
        },
        "string_voice_bus":{
            "voices_per_part":4,"total_lanes":16,
            "channels":{PARTS[p]:[x+1 for x in VOICE_CHANNELS[p]] for p in range(4)},
        },
        "physical_notes":[{"source_id":n.source_id,**physical_note_dict(n)} for n in g.notes],
    })
    score_json.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return out,score_json,g

def main(argv=None):
    ap=argparse.ArgumentParser(description="Compile MusicXML/MXL into SONICRAFT v4.2 physical strings MIDI.")
    ap.add_argument("score",type=Path);ap.add_argument("-o","--out",type=Path);ap.add_argument("--score-json",type=Path)
    a=ap.parse_args(argv)
    try:o,j,g=compile_file(a.score,a.out,a.score_json)
    except Exception as e:print("ERROR:",e,file=sys.stderr);return 2
    print("SONICRAFT v4.2 String Physical Performance Compile OK")
    print("MIDI:",o);print("Score Graph:",j);print("Notes:",len(g.notes),"warnings:",len(g.warnings))
    return 0
if __name__=="__main__":raise SystemExit(main())
