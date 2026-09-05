"""SONICRAFT v4.4 Strings Ensemble Bow & Phrase Compiler.

MusicXML/MXL -> Score Graph -> 4x4 Voice Bus -> v4.2 Physical Plan
-> v4.3 Constraint Solver -> v4.4 Ensemble Coordination
-> editable MIDI + score/constraint/ensemble sidecars.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,struct,sys

from score_expression_graph_v40 import parse_score,graph_dict,PARTS,PPQ
from compile_musicxml_strings_v41 import allocate_voice_lanes,VOICE_CHANNELS,_cc,_stack_cc,_tempo_meta,_time_meta,_key_meta,KS_BASE
from compile_midi_performance_v29 import _track_bytes,_name_event,_meta
from string_physical_graph_v42 import plan_string_physics,physical_note_dict
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble
from string_ensemble_runtime_v44 import attack_norm_from_ms,breath_norm_from_ms

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

def write_midi(g,constraints,ensemble,out:Path):
    conductor=[(0,0,_name_event("SONICRAFT v4.4 Ensemble-Coordinated Strings"))]
    conductor += [(x["tick"],1,_tempo_meta(x["bpm"])) for x in g.tempos]
    conductor += [(x["tick"],1,_time_meta(x["numerator"],x["denominator"])) for x in g.time_signatures]
    conductor += [(x["tick"],1,_key_meta(x["fifths"])) for x in g.key_signatures]
    severity_order={"error":0,"warning":1,"info":2}
    for issue in sorted(constraints.issues,key=lambda x:(x.tick,severity_order.get(x.severity,9),x.kind)):
        conductor.append((max(0,int(issue.tick)),3,_marker(f"SONICRAFT {issue.severity.upper()} {PARTS[issue.part]}: {issue.kind}")))
    for issue in sorted(ensemble.issues,key=lambda x:(x.tick,severity_order.get(x.severity,9),x.kind)):
        conductor.append((max(0,int(issue.tick)),3,_marker(f"SONICRAFT ENSEMBLE {issue.severity.upper()}: {issue.kind}")))

    tracks=[_track_bytes(conductor)]
    global_cmd=[(0,0,bytes([0xB0,117,127])),(0,0,bytes([0xB0,112,0])),
                (0,0,bytes([0xB0,114,127])),(0,0,bytes([0xB0,109,127])),(0,0,bytes([0xB0,110,127]))]
    for p,name in enumerate(PARTS):
        ev=[(0,0,_name_event("SONICRAFT "+name+" · v4.4 Ensemble Voice Bus"))]
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
            transition-=int(round(min(1.0,n.transition_risk)*8))
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
            # v4.4: explicit ensemble timing, still ordinary editable MIDI.
            ev.append((pre,2,bytes([0xB0|ch,36,_cc(attack_norm_from_ms(n.ensemble_attack_offset_ms)*127.0)])))
            ev.append((pre,2,bytes([0xB0|ch,37,_cc(breath_norm_from_ms(n.ensemble_breath_ms)*127.0)])))
            ev.append((n.start_tick,3,bytes([0x90|ch,n.pitch,max(1,min(127,n.velocity))])))
            ev.append((n.end_tick,0,bytes([0x80|ch,n.pitch,0])))
        tracks.append(_track_bytes(ev))
    hdr=b"MThd"+struct.pack(">IHHH",6,1,len(tracks),PPQ)
    out.write_bytes(hdr+b"".join(b"MTrk"+struct.pack(">I",len(tr))+tr for tr in tracks))

def compile_file(src:Path,out:Path|None=None,score_json:Path|None=None,constraints_json:Path|None=None,ensemble_json:Path|None=None):
    g=allocate_voice_lanes(parse_score(src))
    plan_string_physics(g)
    g,constraints=solve_string_constraints(g)
    g,ensemble=coordinate_string_ensemble(g)

    out=out or src.with_name(src.stem+"_SONICRAFT_STRINGS_v44.mid")
    score_json=score_json or out.with_suffix(".score.json")
    constraints_json=constraints_json or out.with_suffix(".constraints.json")
    ensemble_json=ensemble_json or out.with_suffix(".ensemble.json")
    write_midi(g,constraints,ensemble,out)

    data=graph_dict(g)
    data.update({
        "sonicraft_version":"4.4",
        "compiled_midi":out.name,
        "constraint_solver":{
            "repaired_transitions":constraints.repaired_transitions,
            "forced_bow_changes":constraints.forced_bow_changes,
            "unplayable_notes":constraints.unplayable_notes,
            "max_risk":round(float(constraints.max_risk),6),
        },
        "ensemble_coordination":{
            "mode":"full-score deterministic quartet bow/phrase coordination",
            "coordinated_attacks":ensemble.coordinated_attacks,
            "coordinated_bow_directions":ensemble.coordinated_bow_directions,
            "coordinated_bow_changes":ensemble.coordinated_bow_changes,
            "phrase_breaths":ensemble.phrase_breaths,
            "bow_conflicts":ensemble.bow_conflicts,
            "max_attack_spread_ms":round(float(ensemble.max_attack_spread_ms),6),
            "hq_timing_bus":{"36":"signed attack offset -8..+8ms","37":"phrase breath 0..20ms"},
        },
        "physical_notes":[{"source_id":n.source_id,**physical_note_dict(n),
                           "transition_risk":round(float(n.transition_risk),6),
                           "bow_budget":round(float(n.bow_budget),6),
                           "playability_risk":round(float(n.playability_risk),6),
                           "constraint_flags":list(n.constraint_flags),
                           "ensemble_group_id":n.ensemble_group_id,
                           "ensemble_phrase_id":n.ensemble_phrase_id,
                           "ensemble_role":n.ensemble_role,
                           "ensemble_attack_offset_ms":round(float(n.ensemble_attack_offset_ms),6),
                           "ensemble_breath_ms":round(float(n.ensemble_breath_ms),6),
                           "ensemble_bow_sync":n.ensemble_bow_sync,
                           "ensemble_coordination_risk":round(float(n.ensemble_coordination_risk),6),
                           "ensemble_coordination_flags":list(n.ensemble_coordination_flags)}
                          for n in g.notes],
        "string_voice_bus":{"voices_per_part":4,"total_lanes":16,
                            "channels":{PARTS[p]:[x+1 for x in VOICE_CHANNELS[p]] for p in range(4)}},
    })
    score_json.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    constraints_json.write_text(json.dumps(constraints.as_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
    ensemble_json.write_text(json.dumps(ensemble.as_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
    return out,score_json,constraints_json,ensemble_json,g,constraints,ensemble

def main(argv=None):
    ap=argparse.ArgumentParser(description="Compile MusicXML/MXL with SONICRAFT v4.4 Ensemble Coordination.")
    ap.add_argument("score",type=Path);ap.add_argument("-o","--out",type=Path)
    ap.add_argument("--score-json",type=Path);ap.add_argument("--constraints-json",type=Path);ap.add_argument("--ensemble-json",type=Path)
    a=ap.parse_args(argv)
    try:o,s,c,e,g,cr,er=compile_file(a.score,a.out,a.score_json,a.constraints_json,a.ensemble_json)
    except Exception as ex:print("ERROR:",ex,file=sys.stderr);return 2
    print("SONICRAFT v4.4 Ensemble Bow & Phrase Compile OK")
    print("MIDI:",o);print("Score Graph:",s);print("Constraints:",c);print("Ensemble:",e)
    print("notes:",len(g.notes),"attacks:",er.coordinated_attacks,"bow sync:",er.coordinated_bow_directions,
          "breaths:",er.phrase_breaths,"conflicts:",er.bow_conflicts)
    return 0
if __name__=="__main__":raise SystemExit(main())
