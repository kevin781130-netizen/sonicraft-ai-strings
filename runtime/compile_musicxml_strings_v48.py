"""SONICRAFT v4.8 Phrase Performance Critic & Auto-Repair Compiler.

Produces Original D plus three repaired MIDI candidates A/B/C:
A Conservative, B Balanced, C Expressive.

The structural critic is intentionally not an audio judge. It scores performance-control topology,
writes repair candidates, then emits a Judge Queue so the existing v3.7 A/B/C/D Audio Judge can
remain the final sonic authority after rendering.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,sys

from score_expression_graph_v40 import parse_score,graph_dict,PARTS
from compile_musicxml_strings_v41 import allocate_voice_lanes,VOICE_CHANNELS
from string_physical_graph_v42 import plan_string_physics,physical_note_dict
from string_constraint_solver_v43 import solve_string_constraints
from string_ensemble_solver_v44 import coordinate_string_ensemble
from string_gesture_graph_v45 import plan_continuous_string_gestures,gesture_note_dict
from string_transition_graph_v46 import build_continuous_transition_graph_v46,transition_graph_dict
from string_phrase_longline_v47 import plan_phrase_longlines_v47,phrase_graph_dict
from compile_musicxml_strings_v47 import write_midi as write_midi_v47
from string_performance_critic_v48 import generate_repairs_v48,critic_bundle_dict

def _retag_midi_v48(path:Path):
    b=path.read_bytes()
    # v4.7 -> v4.8 is same-length ASCII, safe inside track-name meta payloads.
    path.write_bytes(b.replace(b"v4.7",b"v4.8"))

def _candidate_path(out:Path,slot:str,name:str):
    return out.with_name(out.stem+f"_REPAIR_{slot}_{name.upper()}.mid")

def compile_file(src:Path,out:Path|None=None):
    g=allocate_voice_lanes(parse_score(src))
    plan_string_physics(g)
    g,constraints=solve_string_constraints(g)
    g,ensemble=coordinate_string_ensemble(g)
    g=plan_continuous_string_gestures(g)
    g,links=build_continuous_transition_graph_v46(g)
    g,phrase_arcs=plan_phrase_longlines_v47(g)

    score,issues,candidates,reports,recommended=generate_repairs_v48(g)

    out=out or src.with_name(src.stem+"_SONICRAFT_STRINGS_v48.mid")
    score_json=out.with_suffix(".score.json")
    constraints_json=out.with_suffix(".constraints.json")
    ensemble_json=out.with_suffix(".ensemble.json")
    gesture_json=out.with_suffix(".gesture.json")
    transition_json=out.with_suffix(".transition.json")
    phrase_json=out.with_suffix(".phrase.json")
    critic_json=out.with_suffix(".critic.json")
    judge_queue_json=out.with_suffix(".judge_queue.json")

    # Slot D = untouched v4.7 performance plan, retagged as the v4.8 original.
    write_midi_v47(g,constraints,ensemble,links,out);_retag_midi_v48(out)

    candidate_paths={}
    names={"A":"CONSERVATIVE","B":"BALANCED","C":"EXPRESSIVE"}
    for slot in ("A","B","C"):
        cp=_candidate_path(out,slot,names[slot])
        write_midi_v47(candidates[slot],constraints,ensemble,links,cp);_retag_midi_v48(cp)
        candidate_paths[slot]=cp

    data=graph_dict(g)
    data.update({
        "sonicraft_version":"4.8",
        "compiled_midi":out.name,
        "performance_critic":{
            "original_slot":"D",
            "original_score":score.overall,
            "dimension_scores":score.dimensions,
            "issue_count":score.issue_count,
            "structural_recommendation":recommended,
            "audio_judge_required_for_final_winner":True,
        },
        "repair_candidates":{slot:{
            "strategy":reports[slot].strategy,
            "score_after":reports[slot].score_after,
            "improvement":reports[slot].improvement,
            "midi":candidate_paths[slot].name,
        } for slot in ("A","B","C")},
        "physical_notes":[{"source_id":n.source_id,**physical_note_dict(n),
                           "gesture_profile":n.gesture_profile,
                           "transition_in_link_id":n.transition_in_link_id,
                           "transition_out_link_id":n.transition_out_link_id,
                           "transition_continuity":round(float(n.transition_continuity),6),
                           "phrase_longline_id":n.phrase_longline_id,
                           "phrase_longline_contour":n.phrase_longline_contour,
                           "phrase_bow_reserve":round(float(n.phrase_bow_reserve),6),
                           "phrase_dynamic_momentum":round(float(n.phrase_dynamic_momentum),6),
                           "phrase_vibrato_rate_hz":round(float(n.phrase_vibrato_rate_hz),6)}
                          for n in g.notes],
        "string_voice_bus":{"voices_per_part":4,"total_lanes":16,
                            "channels":{PARTS[p]:[x+1 for x in VOICE_CHANNELS[p]] for p in range(4)}},
    })

    score_json.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    constraints_json.write_text(json.dumps(constraints.as_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
    ensemble_json.write_text(json.dumps(ensemble.as_dict(),ensure_ascii=False,indent=2),encoding="utf-8")
    gesture_json.write_text(json.dumps({"schema":1,"version":"4.8",
                                        "gesture_notes":[gesture_note_dict(n) for n in g.notes if n.gesture_amount>0]},
                                       ensure_ascii=False,indent=2),encoding="utf-8")
    transition_json.write_text(json.dumps(transition_graph_dict(links),ensure_ascii=False,indent=2),encoding="utf-8")
    phrase_json.write_text(json.dumps(phrase_graph_dict(phrase_arcs),ensure_ascii=False,indent=2),encoding="utf-8")

    critic_bundle=critic_bundle_dict(score,issues,reports,recommended)
    critic_bundle["candidate_midis"]={slot:candidate_paths[slot].name for slot in ("A","B","C")}
    critic_bundle["original_midi_D"]=out.name
    critic_json.write_text(json.dumps(critic_bundle,ensure_ascii=False,indent=2),encoding="utf-8")

    judge_queue={
        "schema":1,"version":"4.8",
        "purpose":"render four slots, then use existing SONICRAFT Audio Judge; structural critic is not final sonic authority",
        "slots":{
            "A":{"label":"Conservative Repair","midi":candidate_paths["A"].name},
            "B":{"label":"Balanced Repair","midi":candidate_paths["B"].name},
            "C":{"label":"Expressive Repair","midi":candidate_paths["C"].name},
            "D":{"label":"Original","midi":out.name},
        },
        "structural_recommendation":recommended,
        "final_step":"render A/B/C/D under identical acoustic/runtime settings, then trigger Audio Judge",
    }
    judge_queue_json.write_text(json.dumps(judge_queue,ensure_ascii=False,indent=2),encoding="utf-8")

    return {
        "midi_D":out,"midi_A":candidate_paths["A"],"midi_B":candidate_paths["B"],"midi_C":candidate_paths["C"],
        "score_json":score_json,"constraints_json":constraints_json,"ensemble_json":ensemble_json,
        "gesture_json":gesture_json,"transition_json":transition_json,"phrase_json":phrase_json,
        "critic_json":critic_json,"judge_queue_json":judge_queue_json,
        "graph":g,"score":score,"issues":issues,"reports":reports,"recommended":recommended,
    }

def main(argv=None):
    ap=argparse.ArgumentParser(description="Compile strings score and generate SONICRAFT v4.8 A/B/C auto-repair candidates + D original.")
    ap.add_argument("score",type=Path);ap.add_argument("-o","--out",type=Path)
    a=ap.parse_args(argv)
    try:r=compile_file(a.score,a.out)
    except Exception as ex:print("ERROR:",ex,file=sys.stderr);return 2
    print("SONICRAFT v4.8 Phrase Performance Critic & Auto-Repair OK")
    print("D Original:",r["midi_D"])
    print("A Conservative:",r["midi_A"])
    print("B Balanced:",r["midi_B"])
    print("C Expressive:",r["midi_C"])
    print("Critic:",r["critic_json"])
    print("Judge Queue:",r["judge_queue_json"])
    print("Structural score:",r["score"].overall,"recommendation:",r["recommended"])
    return 0
if __name__=="__main__":raise SystemExit(main())
