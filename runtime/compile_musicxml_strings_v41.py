"""SONICRAFT v4.1 Strings Polyphonic Voice Compiler.

MusicXML/MXL -> editable Type-1 MIDI using a backward-compatible 4x4 String Voice Bus.
Each string part has four explicit MIDI channels so overlapping notes can carry independent
base articulation + Expression Stack + dynamics/vibrato/transition/attack/tightness.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,struct,sys
from score_expression_graph_v40 import parse_score,graph_dict,PARTS,ART_NAMES,PPQ
from compile_midi_performance_v29 import _write_vlq,_track_bytes,_meta,_name_event

KS_BASE=24
VOICE_CHANNELS={
    0:(0,4,5,6),  # Vln I
    1:(1,7,8,9),  # Vln II
    2:(2,10,11,12), # Viola
    3:(3,13,14,15), # Cello
}
def _cc(v):return max(0,min(127,int(round(v))))
def _stack_cc(mask):return _cc((mask&15)/15*127)

def allocate_voice_lanes(g):
    warnings=[]
    for p in range(4):
        ends=[-1]*4
        notes=sorted((n for n in g.notes if n.part==p),key=lambda n:(n.start_tick,n.pitch,n.end_tick))
        for n in notes:
            free=next((i for i,e in enumerate(ends) if e<=n.start_tick),None)
            if free is None:
                free=min(range(4),key=lambda i:(ends[i],i))
                warnings.append({"type":"string_voice_lane_overflow","part":PARTS[p],"tick":n.start_tick,
                                 "pitch":n.pitch,"message":"More than four overlapping independently-expressed notes; earliest lane reused."})
            n.lane_channel=VOICE_CHANNELS[p][free];ends[free]=n.end_tick
    g.warnings.extend(warnings);return g

def _tempo_meta(bpm):
    us=max(1,min(0xFFFFFF,int(round(60_000_000/max(1e-6,float(bpm))))))
    return _meta(0x51,bytes([(us>>16)&255,(us>>8)&255,us&255]))
def _time_meta(num,den):
    dd=0;d=max(1,int(den))
    while (1<<dd)<d and dd<7:dd+=1
    return _meta(0x58,bytes([max(1,min(255,int(num))),dd,24,8]))
def _key_meta(fifths):
    f=max(-7,min(7,int(fifths)));return _meta(0x59,struct.pack("bb",f,0))

def write_midi(g,out:Path):
    conductor=[(0,0,_name_event("SONICRAFT v4.1 Strings Conductor"))]
    conductor += [(x["tick"],1,_tempo_meta(x["bpm"])) for x in g.tempos]
    conductor += [(x["tick"],1,_time_meta(x["numerator"],x["denominator"])) for x in g.time_signatures]
    conductor += [(x["tick"],1,_key_meta(x["fifths"])) for x in g.key_signatures]
    tracks=[_track_bytes(conductor)]
    # Global command lane at tick 0: Q4 Multi, Auto Divisi OFF, independent polyphony ON,
    # MIDI Authority Lock ON, Phrase Director ON.
    global_cmd=[(0,0,bytes([0xB0,117,127])),(0,0,bytes([0xB0,112,0])),
                (0,0,bytes([0xB0,114,127])),(0,0,bytes([0xB0,109,127])),(0,0,bytes([0xB0,110,127]))]
    for p,name in enumerate(PARTS):
        ev=[(0,0,_name_event("SONICRAFT "+name+" · 4x4 String Voice Bus"))]
        if p==0:ev+=global_cmd
        for n in sorted((x for x in g.notes if x.part==p),key=lambda x:(x.start_tick,x.lane_channel,x.pitch)):
            ch=n.lane_channel
            pre=max(0,n.start_tick-max(1,PPQ//96))
            # Per-lane keyswitch + dedicated string voice controls.
            ev.append((pre,1,bytes([0x90|ch,KS_BASE+n.base_art,1])))
            ev.append((n.start_tick,0,bytes([0x80|ch,KS_BASE+n.base_art,0])))
            ev.append((pre,2,bytes([0xB0|ch,21,_stack_cc(n.stack)])))
            ev.append((pre,2,bytes([0xB0|ch,22,_cc(n.cc1)])))
            ev.append((pre,2,bytes([0xB0|ch,23,_cc(n.cc3)])))
            # Physical modifier defaults. These remain editable normal MIDI CC lanes.
            transition=64-(12 if n.stack&2 else 0)-(5 if n.stack&4 else 0)
            attack=48+(22 if n.stack&1 else 0)-(12 if n.stack&8 else 0)
            if "down-bow" in n.technical: attack+=5
            if "up-bow" in n.technical: attack-=3
            tight=64+(10 if n.stack&1 else 0)-(20 if n.stack&4 else 0)
            ev.append((pre,2,bytes([0xB0|ch,24,_cc(transition)])))
            ev.append((pre,2,bytes([0xB0|ch,25,_cc(attack)])))
            ev.append((pre,2,bytes([0xB0|ch,26,_cc(tight)])))
            ev.append((n.start_tick,3,bytes([0x90|ch,n.pitch,max(1,min(127,n.velocity))])))
            ev.append((n.end_tick,0,bytes([0x80|ch,n.pitch,0])))
        tracks.append(_track_bytes(ev))
    hdr=b"MThd"+struct.pack(">IHHH",6,1,len(tracks),PPQ)
    out.write_bytes(hdr+b"".join(b"MTrk"+struct.pack(">I",len(tr))+tr for tr in tracks))

def compile_file(src:Path,out:Path|None=None,score_json:Path|None=None):
    g=allocate_voice_lanes(parse_score(src))
    out=out or src.with_name(src.stem+"_SONICRAFT_STRINGS_v41.mid")
    score_json=score_json or out.with_suffix(".score.json")
    write_midi(g,out)
    data=graph_dict(g)
    data.update({"sonicraft_version":"4.1","compiled_midi":out.name,
                 "string_voice_bus":{"voices_per_part":4,"total_lanes":16,"channels":{PARTS[p]:[x+1 for x in VOICE_CHANNELS[p]] for p in range(4)},
                                     "cc":{"21":"Expression Stack bitmask","22":"Lane Dynamics","23":"Lane Vibrato","24":"Transition Speed","25":"Attack Character","26":"Short Tightness"}}})
    score_json.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return out,score_json,g

def main(argv=None):
    ap=argparse.ArgumentParser(description="Compile MusicXML/MXL into SONICRAFT v4.1 strings-only per-note expression MIDI.")
    ap.add_argument("score",type=Path);ap.add_argument("-o","--out",type=Path);ap.add_argument("--score-json",type=Path)
    a=ap.parse_args(argv)
    try:o,j,g=compile_file(a.score,a.out,a.score_json)
    except Exception as e:print("ERROR:",e,file=sys.stderr);return 2
    print("SONICRAFT v4.1 Strings Polyphonic Voice Compile OK")
    print("MIDI:",o);print("Score Graph:",j);print("Notes:",len(g.notes),"warnings:",len(g.warnings))
    return 0
if __name__=="__main__":raise SystemExit(main())
