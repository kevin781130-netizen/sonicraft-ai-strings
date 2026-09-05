"""SONICRAFT v5.1 Selective-Repair-capable A/B/C/D compiler.

Initial compile and every accepted iteration use the same pipeline. The only learned state is the
small local RepairPolicyMemoryV49 multiplier vector. D is always the untouched base performance.
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
from string_repair_policy_v49 import RepairPolicyMemoryV49,default_policy_path

def _retag(path:Path):
    b=path.read_bytes()
    for old in (b"v4.7",b"v4.8"):
        b=b.replace(old,b"v5.1")
    path.write_bytes(b)

def _candidate_path(out,slot,name):
    return out.with_name(out.stem+f"_REPAIR_{slot}_{name}.mid")

def compile_file(src:Path,out:Path|None=None,policy_path:Path|None=None,round_index:int=1):
    src=Path(src);round_index=max(1,int(round_index))
    mem=RepairPolicyMemoryV49(policy_path)
    snap=mem.snapshot()

    g=allocate_voice_lanes(parse_score(src))
    plan_string_physics(g)
    g,constraints=solve_string_constraints(g)
    g,ensemble=coordinate_string_ensemble(g)
    g=plan_continuous_string_gestures(g)
    g,links=build_continuous_transition_graph_v46(g)
    g,phrase_arcs=plan_phrase_longlines_v47(g)

    score,issues,candidates,reports,recommended=generate_repairs_v48(g,policy=snap.values)

    out=out or src.with_name(src.stem+f"_SONICRAFT_STRINGS_v51_R{round_index}.mid")
    out=Path(out)
    names={"A":"CONSERVATIVE","B":"BALANCED","C":"EXPRESSIVE"}

    score_json=out.with_suffix(".score.json")
    constraints_json=out.with_suffix(".constraints.json")
    ensemble_json=out.with_suffix(".ensemble.json")
    gesture_json=out.with_suffix(".gesture.json")
    transition_json=out.with_suffix(".transition.json")
    phrase_json=out.with_suffix(".phrase.json")
    critic_json=out.with_suffix(".critic.json")
    policy_json=out.with_suffix(".policy_snapshot.json")
    judge_queue_json=out.with_suffix(".judge_queue.json")

    write_midi_v47(g,constraints,ensemble,links,out);_retag(out)
    candidate_paths={}
    for slot in "ABC":
        cp=_candidate_path(out,slot,names[slot])
        write_midi_v47(candidates[slot],constraints,ensemble,links,cp);_retag(cp)
        candidate_paths[slot]=cp

    data=graph_dict(g)
    data.update({
        "sonicraft_version":"5.1",
        "compiled_midi":out.name,
        "round_index":round_index,
        "repair_policy":{
            "generation":snap.generation,"evidence":snap.evidence,"confidence":snap.confidence,
            "profile_hash":snap.profile_hash,"values":snap.values,
        },
        "performance_critic":{
            "original_slot":"D","original_score":score.overall,"dimension_scores":score.dimensions,
            "issue_count":score.issue_count,"structural_recommendation":recommended,
            "audio_judge_required_for_final_winner":True,
        },
        "repair_candidates":{slot:{
            "strategy":reports[slot].strategy,"score_after":reports[slot].score_after,
            "improvement":reports[slot].improvement,"midi":candidate_paths[slot].name,
        } for slot in "ABC"},
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
    gesture_json.write_text(json.dumps({"schema":1,"version":"5.1",
                                        "gesture_notes":[gesture_note_dict(n) for n in g.notes if n.gesture_amount>0]},
                                       ensure_ascii=False,indent=2),encoding="utf-8")
    transition_json.write_text(json.dumps(transition_graph_dict(links),ensure_ascii=False,indent=2),encoding="utf-8")
    phrase_json.write_text(json.dumps(phrase_graph_dict(phrase_arcs),ensure_ascii=False,indent=2),encoding="utf-8")

    cb=critic_bundle_dict(score,issues,reports,recommended)
    cb.update({
        "version":"5.1","round_index":round_index,
        "policy_generation":snap.generation,"policy_hash":snap.profile_hash,"policy_values":snap.values,
        "candidate_midis":{slot:candidate_paths[slot].name for slot in "ABC"},
        "original_midi_D":out.name,
    })
    critic_json.write_text(json.dumps(cb,ensure_ascii=False,indent=2),encoding="utf-8")

    policy_json.write_text(json.dumps({
        "schema":1,"version":"5.1","generation":snap.generation,"evidence":snap.evidence,
        "confidence":snap.confidence,"profile_hash":snap.profile_hash,"values":snap.values,
        "persistent_policy_path":str(mem.path),
    },ensure_ascii=False,indent=2),encoding="utf-8")

    queue={
        "schema":2,"version":"5.1","round_index":round_index,
        "source_score":str(src.resolve()),
        "queue_dir":str(out.parent.resolve()),
        "policy_path":str(mem.path),
        "policy_generation":snap.generation,"policy_hash":snap.profile_hash,
        "policy_values":snap.values,
        "purpose":"render A/B/C/D identically, then run v5.1 post-render iteration",
        "slots":{
            "A":{"label":"Conservative Repair","midi":candidate_paths["A"].name,
                 "expected_render":candidate_paths["A"].with_suffix(".wav").name},
            "B":{"label":"Balanced Repair","midi":candidate_paths["B"].name,
                 "expected_render":candidate_paths["B"].with_suffix(".wav").name},
            "C":{"label":"Expressive Repair","midi":candidate_paths["C"].name,
                 "expected_render":candidate_paths["C"].with_suffix(".wav").name},
            "D":{"label":"Original","midi":out.name,"expected_render":out.with_suffix(".wav").name},
        },
        "structural_recommendation":recommended,
        "learning_gate":{"min_audio_margin":.025,"safety_floor":.35,"overall_floor":.35,
                         "all_four_renders_required":True,"stale_policy_rejected":True},
        "shadow_auto_loop":{"supported":True,"default_sample_rate":48000,"chunk_seconds":40.0,"overlap_seconds":.75,"max_round":6},
        "selective_phrase_search":{"supported":True,"coverage_fallback":.55,"max_windows":6,
                                   "local_context_seconds":.85,"full_render_fallback":True},
        "next_command":"AUTO_LOOP_STRINGS_v51.bat <source score>",
    }
    judge_queue_json.write_text(json.dumps(queue,ensure_ascii=False,indent=2),encoding="utf-8")

    return {
        "midi_D":out,"midi_A":candidate_paths["A"],"midi_B":candidate_paths["B"],"midi_C":candidate_paths["C"],
        "score_json":score_json,"critic_json":critic_json,"policy_json":policy_json,
        "judge_queue_json":judge_queue_json,"graph":g,"score":score,"reports":reports,
        "recommended":recommended,"policy_snapshot":snap,
    }

def main(argv=None):
    ap=argparse.ArgumentParser(description="SONICRAFT v5.1 Selective-Repair-capable Strings compiler.")
    ap.add_argument("score",type=Path);ap.add_argument("-o","--out",type=Path)
    ap.add_argument("--policy",type=Path,default=None)
    ap.add_argument("--round",type=int,default=1)
    a=ap.parse_args(argv)
    try:r=compile_file(a.score,a.out,a.policy,a.round)
    except Exception as ex:print("ERROR:",ex,file=sys.stderr);return 2
    print("SONICRAFT v5.1 Shadow Auto-Loop Compile OK")
    print("Round:",a.round,"Policy generation:",r["policy_snapshot"].generation,
          "confidence:",round(r["policy_snapshot"].confidence,4))
    for slot in "ABCD":print(slot+":",r["midi_"+slot])
    print("Judge Queue:",r["judge_queue_json"])
    return 0
if __name__=="__main__":raise SystemExit(main())
