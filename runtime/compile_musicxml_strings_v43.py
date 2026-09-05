"""SONICRAFT v4.3 Strings Constraint & Transition Compiler.

Pipeline:
MusicXML/MXL -> semantic Score Graph -> 4x4 voice allocation -> v4.2 physical plan
-> v4.3 future-aware constraint/transition solve -> editable MIDI + report JSON.

The solver never invents missing acoustic techniques and does not run in the audio callback.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,struct,sys

from score_expression_graph_v40 import parse_score,graph_dict,PARTS,PPQ
from compile_musicxml_strings_v41 import allocate_voice_lanes,VOICE_CHANNELS,_cc,_stack_cc,_tempo_meta,_time_meta,_key_meta,KS_BASE
from compile_midi_performance_v29 import _track_bytes,_name_event,_meta
from string_physical_graph_v42 import plan_string_physics,physical_note_dict
from string_constraint_solver_v43 import solve_string_constraints

def _marker(text:str):
    return _meta(0x06,text.encode("utf-8","replace")[:220])

def _phys_cc_values(n):
    return {
        27:_cc((max(0,min(3,n.string_index))/3.0)*127.0),
        28:_cc((max(0,min(8,n.position_index))/8.0)*127.0),
        29:127 if int(n.bow_direction)==1 else 0,
        30:127 if n.bow_change else 0,
        31:_cc(float(n.bow_pressure)*127.0),
        33:_cc(float(n.contact_point)*127.0),
        34:_cc(float(n.portamento_route)*127.0),
        35:_cc((max(0,min(3,n.divisi_desk))/3.0)*127.0),
    }

def write_midi(g,report,out:Path):
    conductor=[(0,0,_name_event("SONICRAFT v4.3 Strings Constraint Conductor"))]
    conductor += [(x["tick"],1,_tempo_meta(x["bpm"])) for x in g.tempos]
    conductor += [(x["tick"],1,_time_meta(x["numerator"],x["denominator"])) for x in g.time_signatures]
    conductor += [(x["tick"],1,_key_meta(x["fifths"])) for x in g.key_signatures]
    severity_order={"error":0,"warning":1,"info":2}
    for issue in sorted(report.issues,key=lambda x:(x.tick,severity_order.get(x.severity,9),x.kind)):
        label=f"SONICRAFT {issue.severity.upper()} {PARTS[issue.part]}: {issue.kind}"
        conductor.append((max(0,int(issue.tick)),3,_marker(label)))
    tracks=[_track_bytes(conductor)]

    global_cmd=[(0,0,bytes([0xB0,117,127])),(0,0,bytes([0xB0,112,0])),
                (0,0,bytes([0xB0,114,127])),(0,0,bytes([0xB0,109,127])),(0,0,bytes([0xB0,110,127]))]
    for p,name in enumerate(PARTS):
        ev=[(0,0,_name_event("SONICRAFT "+name+" · v4.3 Constraint-Solved Voice Bus"))]
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
            # High transition risk softens the requested transition rather than inventing a new articulation.
            transition -= int(round(min(1.0,n.transition_risk)*8))
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

def compile_file(src:Path,out:Path|None=None,score_json:Path|None=None,constraints_json:Path|None=None):
    g=allocate_voice_lanes(parse_score(src))
    plan_string_physics(g)
    g,report=solve_string_constraints(g)
    out=out or src.with_name(src.stem+"_SONICRAFT_STRINGS_v43.mid")
    score_json=score_json or out.with_suffix(".score.json")
    constraints_json=constraints_json or out.with_suffix(".constraints.json")
    write_midi(g,report,out)

    data=graph_dict(g)
    data.update({
        "sonicraft_version":"4.3",
        "compiled_midi":out.name,
        "constraint_solver":{
            "mode":"future-aware deterministic strings ergonomics",
            "hard_limits_are_warnings_not_acoustic_fabrication":True,
            "repaired_transitions":report.repaired_transitions,
            "forced_bow_changes":report.forced_bow_changes,
            "unplayable_notes":report.unplayable_notes,
            "max_risk":round(float(report.max_risk),6),
        },
        "physical_notes":[{"source_id":n.source_id,**physical_note_dict(n),
                           "transition_risk":round(float(n.transition_risk),6),
                           "bow_budget":round(float(n.bow_budget),6),
                           "playability_risk":round(float(n.playability_risk),6),
                           "constraint_flags":list(n.constraint_flags),
                           "multi_stop_group_id":n.multi_stop_group_id,
                           "multi_stop_feasible":n.multi_stop_feasible,
                           "divisi_required":n.divisi_required}
                          for n in g.notes],
        "string_voice_bus":{"voices_per_part":4,"total_lanes":16,
                            "channels":{PARTS[p]:[x+1 for x in VOICE_CHANNELS[p]] for p in range(4)}},
    })
    score_json.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    constraints_json.write_text(json.dumps(report.as_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
    return out,score_json,constraints_json,g,report

def main(argv=None):
    ap=argparse.ArgumentParser(description="Compile MusicXML/MXL with SONICRAFT v4.3 String Constraint & Transition Solver.")
    ap.add_argument("score",type=Path);ap.add_argument("-o","--out",type=Path)
    ap.add_argument("--score-json",type=Path);ap.add_argument("--constraints-json",type=Path)
    a=ap.parse_args(argv)
    try:o,j,c,g,r=compile_file(a.score,a.out,a.score_json,a.constraints_json)
    except Exception as e:print("ERROR:",e,file=sys.stderr);return 2
    print("SONICRAFT v4.3 String Constraint & Transition Compile OK")
    print("MIDI:",o);print("Score Graph:",j);print("Constraint Report:",c)
    print("notes:",len(g.notes),"repaired:",r.repaired_transitions,"bow changes:",r.forced_bow_changes,
          "unplayable:",r.unplayable_notes,"max risk:",round(r.max_risk,3))
    return 0
if __name__=="__main__":raise SystemExit(main())
