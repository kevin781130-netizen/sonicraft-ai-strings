"""SONICRAFT v6.0 Unified Evidence Store / Memory Consolidation Auto-Loop.

Normal path:
  compile -> locate problem phrases -> local A/B/C/D Shadow renders -> local Audio Judge
  -> selectively merge winning MIDI regions -> gated policy learning -> next round if useful
  -> ONE final full render of the merged MIDI.

Conservative fallback:
  if localization is diffuse, a local window is too large, or any local Judge decision is
  low-confidence, run the proven v5.0-style full A/B/C/D round instead.
"""
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,shutil,sys,time

from compile_musicxml_strings_v60 import compile_file
from string_performance_critic_v48 import evaluate_performance_v48
from selective_phrase_search_v51 import build_selective_plan_v51
from shadow_render_selective_v51 import render_midi_window_v51,tick_window_to_samples_v51
from selective_midi_merge_v51 import splice_midi_windows_v51
from conductor_intent_v53 import choose_conductor_locked_decisions_v53
from conductor_candidate_steering_v54 import render_slots_for_window_v54
from candidate_utility_predictor_v55 import CandidateUtilityMemoryV55,should_escalate_v55,default_utility_path
from context_similarity_transfer_v57 import SimilarityTransferMemoryV57,default_transfer_path_v57
from performance_archetype_memory_v58 import PerformanceArchetypeMemoryV58,default_archetype_path_v58
from archetype_mixture_v59 import ArchetypeMixtureMemoryV59,predict_candidate_utility_v59,learn_mixture_rendered_v59,default_mixture_path_v59
from counterfactual_auditor_v56 import CounterfactualAuditMemoryV56,default_audit_path_v56
from evidence_store_v60 import UnifiedEvidenceStoreV60,default_evidence_store_path_v60
from shadow_render_auto_v50 import start_shadow_service_v50,render_midi_v50,compiled_midi_to_shadow_events_v50
from audio_io_v49 import load_render_set_v49
from midi_judge_adapter_v49 import midi_to_judge_events_v49
from audio_take_judge_v37 import judge_take,score_dict
from string_repair_policy_v49 import RepairPolicyMemoryV49,MIN_MARGIN,SAFETY_FLOOR,OVERALL_FLOOR

SLOTS="ABCD"
MAX_ROUND=6
DOMINANCE_FLOOR=.60

def _queue_midis(qpath,q):
    d=Path(qpath).parent
    return {s:d/q["slots"][s]["midi"] for s in SLOTS}

def _judge_full_round(qpath):
    qpath=Path(qpath);q=json.loads(qpath.read_text(encoding="utf-8"));d=qpath.parent
    paths={s:d/q["slots"][s]["expected_render"] for s in SLOTS}
    audios,sr,frames=load_render_set_v49([paths[s] for s in SLOTS])
    scores={}
    for slot,audio in zip(SLOTS,audios):
        midi=d/q["slots"][slot]["midi"]
        ev=midi_to_judge_events_v49(midi,sr,frames)
        scores[slot]=judge_take(audio,sr,ev,0,frames)
    rank=sorted(SLOTS,key=lambda s:scores[s].overall,reverse=True)
    winner,runner=rank[:2];margin=float(scores[winner].overall-scores[runner].overall)
    return q,paths,scores,winner,runner,margin

def _copy_final(src_score,out_dir,midi,wav,label):
    out_dir=Path(out_dir);stem=Path(src_score).stem
    mo=out_dir/f"{stem}_SONICRAFT_STRINGS_v60_{label}.mid"
    wo=out_dir/f"{stem}_SONICRAFT_STRINGS_v60_{label}.wav"
    shutil.copy2(midi,mo);shutil.copy2(wav,wo)
    return mo,wo

def _aggregate_local_learning(decisions):
    totals={s:0.0 for s in SLOTS}
    for d in decisions:
        dur=max(.05,float(d["duration_seconds"]))
        w=dur*max(MIN_MARGIN,float(d["margin"]))
        totals[d["winner"]]+=w
    total=sum(totals.values())
    if total<=0:return {"accepted":False,"reason":"no_local_evidence"}
    winner=max(SLOTS,key=lambda s:totals[s]);share=totals[winner]/total
    rows=[d for d in decisions if d["winner"]==winner]
    if share<DOMINANCE_FLOOR:
        return {"accepted":False,"reason":"mixed_local_winners","dominant":winner,"share":share}
    weights=[max(.05,float(d["duration_seconds"]))*max(MIN_MARGIN,float(d["margin"])) for d in rows]
    den=max(1e-9,sum(weights))
    margin=sum(w*float(d["margin"]) for w,d in zip(weights,rows))/den
    safety=sum(w*float(d["scores"][winner]["safety"]) for w,d in zip(weights,rows))/den
    overall=sum(w*float(d["scores"][winner]["overall"]) for w,d in zip(weights,rows))/den
    return {"accepted":True,"winner":winner,"share":share,"margin":margin,"safety":safety,"overall":overall}

def _render_full_abcd(qpath,host,port,sr,chunk,overlap,round_index):
    q=json.loads(Path(qpath).read_text(encoding="utf-8"));d=Path(qpath).parent
    info={}
    for si,s in enumerate(SLOTS):
        midi=d/q["slots"][s]["midi"];wav=d/q["slots"][s]["expected_render"]
        info[s]=render_midi_v50(midi,wav,host,port,sr,chunk,overlap,
                                request_seed=551000+round_index*100+si*10)
    return info

def _full_fallback_round(score,out_dir,qpath,host,port,sr,chunk,overlap,round_index,reason):
    render_info=_render_full_abcd(qpath,host,port,sr,chunk,overlap,round_index)
    q,paths,scores,winner,runner,margin=_judge_full_round(qpath)
    mem=RepairPolicyMemoryV49(q["policy_path"]);before=mem.snapshot()
    stale=(before.generation!=int(q["policy_generation"]) or before.profile_hash!=str(q["policy_hash"]))
    ws=scores[winner]
    learn={"learned":False,"reason":"stale_policy"} if stale else mem.learn(winner,margin,ws.safety,ws.overall)
    after=mem.snapshot()
    row={
        "mode":"full_fallback","fallback_reason":reason,"winner":winner,"runner_up":runner,
        "margin":round(margin,9),"scores":{s:score_dict(scores[s]) for s in SLOTS},
        "renders":{s:{k:(str(v) if isinstance(v,Path) else v) for k,v in render_info[s].items()} for s in SLOTS},
        "learning":{"accepted":bool(learn.get("learned")),"reason":learn.get("reason")},
        "policy_before":{"generation":before.generation,"hash":before.profile_hash,"values":before.values},
        "policy_after":{"generation":after.generation,"hash":after.profile_hash,"values":after.values},
    }
    return row,q,paths,bool(learn.get("learned"))

def run_auto_loop_v60(score,out_dir=None,policy_path=None,host="127.0.0.1",port=49337,
                      backend="auto",model_dir=None,cache_dir=None,mock=False,max_round=MAX_ROUND,
                      sample_rate=48000,chunk_seconds=40.0,overlap_seconds=.75,max_windows=6,
                      coverage_limit=.55,local_context=.85,max_local_context_seconds=28.0,
                      utility_memory_path=None,audit_memory_path=None,transfer_memory_path=None,
                      archetype_memory_path=None,mixture_memory_path=None,evidence_store_path=None):
    score=Path(score).resolve()
    if not score.exists():raise FileNotFoundError(score)
    out_dir=Path(out_dir) if out_dir else score.with_name(score.stem+"_SONICRAFT_v60_SELECTIVE")
    out_dir.mkdir(parents=True,exist_ok=True)

    utility_path=Path(utility_memory_path or default_utility_path(policy_path))
    audit_path_mem=Path(audit_memory_path or default_audit_path_v56(utility_path))
    transfer_path_mem=Path(transfer_memory_path or default_transfer_path_v57(utility_path))
    archetype_path_mem=Path(archetype_memory_path or default_archetype_path_v58(utility_path))
    mixture_path_mem=Path(mixture_memory_path or default_mixture_path_v59(utility_path))
    evidence_paths={
        "utility_v55":utility_path,
        "audit_v56":audit_path_mem,
        "similarity_v57":transfer_path_mem,
        "archetype_v58":archetype_path_mem,
        "mixture_v59":mixture_path_mem,
    }
    evidence_store=UnifiedEvidenceStoreV60(
        evidence_store_path or default_evidence_store_path_v60(utility_path)
    )
    evidence_bootstrap=evidence_store.bootstrap_or_recover(evidence_paths)

    # Instantiate legacy compatibility objects only AFTER transactional recovery.
    utility_mem=CandidateUtilityMemoryV55(utility_path)
    audit_mem=CounterfactualAuditMemoryV56(audit_path_mem)
    transfer_mem=SimilarityTransferMemoryV57(transfer_path_mem)
    archetype_mem=PerformanceArchetypeMemoryV58(archetype_path_mem)
    mixture_mem=ArchetypeMixtureMemoryV59(mixture_path_mem)
    max_round=max(1,min(MAX_ROUND,int(max_round)))
    spawned=None;trace=[];final=None;start=time.time()
    last_merged=None
    try:
        spawned,_=start_shadow_service_v50(host,port,mock,backend,model_dir,cache_dir)
        for round_index in range(1,max_round+1):
            out=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}.mid")
            comp=compile_file(score,out,policy_path,round_index)
            qpath=Path(comp["judge_queue_json"]);q=json.loads(qpath.read_text(encoding="utf-8"))
            issues_score,issues=evaluate_performance_v48(comp["graph"])
            plan=build_selective_plan_v51(comp["graph"],issues,comp["reports"],
                                          max_windows=max_windows,coverage_limit=coverage_limit)

            # Preflight actual seconds. Extremely long "local" windows are not economically local.
            if plan.selective:
                try:
                    for w in plan.windows:
                        a,b=tick_window_to_samples_v51(comp["midi_D"],w.start_tick,w.end_tick,sample_rate)
                        seconds=(b-a)/float(sample_rate)+2*float(local_context)
                        if seconds>float(max_local_context_seconds):
                            raise ValueError(f"window_{w.window_id}_too_long:{seconds:.3f}s")
                except Exception as ex:
                    plan.selective=False;plan.fallback_reason=f"local_window_preflight:{ex}"

            if not plan.selective:
                row,qfull,paths,learned=_full_fallback_round(
                    score,out_dir,qpath,host,port,sample_rate,chunk_seconds,overlap_seconds,
                    round_index,plan.fallback_reason or "selective_not_applicable")
                row.update({"round":round_index,"plan":plan.as_dict()});trace.append(row)
                if not learned:
                    midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row["winner"]]["midi"],
                                         paths[row["winner"]],"REVIEW_BEST")
                    final={"status":"review_required","mode":"full_fallback","round":round_index,
                           "reason":row["learning"]["reason"],"winner":row["winner"],
                           "midi":str(midi),"wav":str(wav),"margin":row["margin"]}
                    break
                if round_index>=max_round:
                    midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row["winner"]]["midi"],
                                         paths[row["winner"]],"WINNER")
                    final={"status":"round_cap","mode":"full_fallback","round":round_index,
                           "winner":row["winner"],"midi":str(midi),"wav":str(wav),"margin":row["margin"]}
                    break
                continue

            midis=_queue_midis(qpath,q)
            decisions=[];local_cost_frames=0;low_conf=None
            local_dir=out_dir/f"R{round_index}_LOCAL"
            local_dir.mkdir(exist_ok=True)

            candidate_renders_skipped=0
            candidate_renders_escalated=0
            candidate_renders_audited=0
            utility_predictions=[]
            utility_updates=[]
            audit_plans=[]
            audit_events=[]
            transfer_events=[]
            archetype_updates=[]
            archetype_audit_events=[]
            mixture_audit_events=[]
            for wi,w in enumerate(plan.windows):
                slot_results={};scores={};rendered=[]
                v54_budget=render_slots_for_window_v54(comp["conductor_intent"],w.start_tick,w.end_tick)
                prediction=predict_candidate_utility_v59(
                    v54_budget["character"],w.dimensions,comp.get("steered_scores"),comp.get("reports"),
                    comp["policy_snapshot"].values,utility_mem,audit_mem,transfer_mem,
                    archetype_mem,mixture_mem,comp["archetype_mixture"],v54_budget["active"]
                )
                audit_plan=audit_mem.plan(prediction,v54_budget["active"])
                active=list(audit_plan.initial_slots);deferred=list(audit_plan.pruned_slots)
                audit_plans.append(audit_plan.as_dict())

                def render_slot(slot,serial):
                    nonlocal local_cost_frames
                    lwav=local_dir/f"W{w.window_id:02d}_{slot}.wav"
                    rr=render_midi_window_v51(
                        midis[slot],w.start_tick,w.end_tick,lwav,host,port,sample_rate,
                        preroll=local_context,postroll=local_context,
                        request_id=5550000+round_index*10000+wi*100+serial*10,
                        max_context_seconds=max_local_context_seconds
                    )
                    slot_results[slot]=rr
                    local_cost_frames+=int(rr["context_frames"])
                    scores[slot]=judge_take(rr["audio"],sample_rate,rr["events"],
                                            rr["core_start_sample"],rr["core_end_sample"])
                    rendered.append(slot)

                for si,slot in enumerate(active):render_slot(slot,si)

                def current_rank():
                    rank=sorted(scores,key=lambda s:scores[s].overall,reverse=True)
                    winner,runner=rank[:2]
                    return rank,winner,runner,float(scores[winner].overall-scores[runner].overall)

                rank,winner,runner,margin=current_rank()
                initial_margin=margin
                preaudit_scores={s:score_dict(scores[s]) for s in rendered}
                preaudit_winner=winner
                # Hypothetical v5.5 winner is computed only from the predictor's original initial set.
                hypothetical_available=[s for s in audit_plan.hypothetical_initial_slots if s in scores]
                if len(hypothetical_available)>=2:
                    hrank=sorted(hypothetical_available,key=lambda s:scores[s].overall,reverse=True)
                    preaudit_winner=hrank[0]
                    preaudit_scores={s:score_dict(scores[s]) for s in hypothetical_available}

                escalate,escalate_reason=should_escalate_v55(prediction,scores,winner,margin)
                expanded=False;audit_expanded=False;audit_record=None
                if escalate and deferred:
                    expanded=True
                    for di,slot in enumerate(deferred,len(active)):
                        render_slot(slot,di);candidate_renders_escalated+=1
                    rank,winner,runner,margin=current_rank()
                elif audit_plan.audit_due:
                    audit_expanded=True
                    for di,slot in enumerate(audit_plan.audit_slots,len(rendered)):
                        if slot not in rendered:
                            render_slot(slot,di);candidate_renders_audited+=1
                    rank,winner,runner,margin=current_rank()
                    # Audit always uses full A/B/C/D evidence; if all slots were already in the
                    # widened budget, this still records the counterfactual v5.5 decision.
                    if len(rendered)==4 and len(preaudit_scores)>=2:
                        audit_record=audit_mem.record_audit(
                            prediction.context_key,preaudit_scores,preaudit_winner,
                            {s:score_dict(scores[s]) for s in rendered},winner,
                            audit_plan.hypothetical_pruned_slots
                        )
                        audit_events.append(audit_record)
                        transfer_record=transfer_mem.record_audit(
                            prediction.context_key,prediction.transfer_donors,audit_record
                        )
                        if transfer_record.get("recorded"):transfer_events.append(transfer_record)
                        if prediction.mixture_evidence>0:
                            mix_audit=mixture_mem.record_audit(
                                prediction.context_key,prediction.mixture_components,audit_record
                            )
                            if mix_audit.get("recorded"):mixture_audit_events.append(mix_audit)
                else:
                    candidate_renders_skipped+=len(deferred)

                ws=scores[winner]
                accepted_local=(margin>=MIN_MARGIN and ws.safety>=SAFETY_FLOOR and ws.overall>=OVERALL_FLOOR)
                update={"learned":False,"reason":"local_gate_not_passed"}
                arche_update={"learned":False,"reason":"local_gate_not_passed"}
                if accepted_local:
                    rendered_score_dict={s:score_dict(scores[s]) for s in rendered}
                    update=utility_mem.learn_rendered(prediction.context_key,rendered_score_dict,winner,full_evidence=(len(rendered)==4))
                    arche_update=learn_mixture_rendered_v59(
                        archetype_mem,comp["archetype_mixture"],prediction.context_key,
                        rendered_score_dict,winner,full_evidence=(len(rendered)==4)
                    )
                utility_updates.append(update)
                archetype_updates.append(arche_update)
                utility_predictions.append(prediction.as_dict())

                d={
                    "window_id":w.window_id,"start_tick":w.start_tick,"end_tick":w.end_tick,
                    "phrase_keys":w.phrase_keys,"dimensions":w.dimensions,"priority":w.priority,
                    "winner":winner,"runner_up":runner,"margin":round(margin,9),
                    "duration_seconds":slot_results[winner]["frames"]/float(sample_rate),
                    "scores":{s:score_dict(scores[s]) for s in rendered},
                    "local_wavs":{s:str(slot_results[s]["wav"]) for s in rendered},
                    "context_seconds":slot_results[winner]["context_seconds"],
                    "candidate_budget":{
                        "section_id":v54_budget["section_id"],"character":v54_budget["character"],
                        "v54_primary_slots":v54_budget["active"],
                        "predicted_ranking":prediction.ranking,"predicted_scores":prediction.scores,
                        "predictor_confidence":prediction.confidence,"predicted_margin":prediction.predicted_margin,
                        "utility_context":prediction.context_key,"utility_reason":prediction.reason,
                        "local_utility_evidence":prediction.local_evidence,
                        "transferred_utility_evidence":prediction.transfer_evidence,
                        "transfer_confidence":prediction.transfer_confidence,
                        "transfer_donors":prediction.transfer_donors,
                        "transfer_detail":prediction.transfer_detail,
                        "archetype_label":comp["archetype"].label,
                        "archetype_classification_confidence":comp["archetype"].confidence,
                        "mixture_confidence":prediction.mixture_confidence,
                        "mixture_evidence":prediction.mixture_evidence,
                        "mixture_components":prediction.mixture_components,
                        "mixture_detail":prediction.mixture_detail,
                        "audit_guard":audit_plan.as_dict(),
                        "effective_predictor_confidence":audit_plan.effective_confidence,
                        "primary_slots":active,"deferred_slots":deferred,
                        "rendered_slots":list(rendered),"expanded":expanded or audit_expanded,
                        "standard_escalation":expanded,"counterfactual_audit":audit_expanded,
                        "audit_record":audit_record,
                        "escalate_reason":escalate_reason,
                        "initial_margin":round(initial_margin,9),"final_margin":round(margin,9),
                        "utility_memory_update":update,
                        "archetype_memory_update":arche_update,
                    },
                }
                decisions.append(d)
                if margin<MIN_MARGIN:low_conf=f"local_low_margin_W{w.window_id}"
                elif ws.safety<SAFETY_FLOOR:low_conf=f"local_safety_floor_W{w.window_id}"
                elif ws.overall<OVERALL_FLOOR:low_conf=f"local_low_overall_W{w.window_id}"
                if low_conf:break

            evidence_commit=evidence_store.capture_legacy(
                evidence_paths,f"round_{round_index}_local_evidence_transaction"
            )
            evidence_verify=evidence_store.verify_legacy(evidence_paths)
            if not evidence_verify["all_match"]:
                raise RuntimeError("evidence_store_post_commit_verification_failed")

            if low_conf:
                # Local ambiguity means the window assumption is not trusted. Fall back to the
                # proven whole-song A/B/C/D Judge for this round.
                row,qfull,paths,learned=_full_fallback_round(
                    score,out_dir,qpath,host,port,sample_rate,chunk_seconds,overlap_seconds,
                    round_index,low_conf)
                row.update({"round":round_index,"plan":plan.as_dict(),
                            "local_decisions_before_fallback":decisions,
                            "candidate_renders_skipped":candidate_renders_skipped,
                            "candidate_renders_escalated":candidate_renders_escalated,
                            "evidence_transaction":evidence_commit,
                            "evidence_store_head":evidence_store.head,
                            "local_render_equivalent_full":None})
                trace.append(row)
                if not learned:
                    midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row["winner"]]["midi"],
                                         paths[row["winner"]],"REVIEW_BEST")
                    final={"status":"review_required","mode":"full_fallback_after_local",
                           "round":round_index,"reason":row["learning"]["reason"],
                           "winner":row["winner"],"midi":str(midi),"wav":str(wav),"margin":row["margin"]}
                    break
                if round_index>=max_round:
                    midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row["winner"]]["midi"],
                                         paths[row["winner"]],"WINNER")
                    final={"status":"round_cap","mode":"full_fallback_after_local",
                           "round":round_index,"winner":row["winner"],
                           "midi":str(midi),"wav":str(wav),"margin":row["margin"]}
                    break
                continue

            utility_path=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}.candidate_utility.json")
            utility_path.write_text(json.dumps({
                "schema":1,"version":"6.0","memory_path":str(utility_mem.path),
                "memory_generation":utility_mem.generation,"predictions":utility_predictions,
                "updates":utility_updates,"actual_render_only_learning":True
            },ensure_ascii=False,indent=2),encoding="utf-8")
            audit_path=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}.counterfactual_audit.json")
            audit_path.write_text(json.dumps({
                "schema":1,"version":"6.0","memory_path":str(audit_mem.path),
                "memory_generation":audit_mem.generation,"plans":audit_plans,"events":audit_events,
                "false_prune_margin":.025,"base_audit_interval":12,
                "context_disable_rate":.25,"recovery_clean_audits":4,
                "privacy":"aggregate outcomes only; no audio/MIDI/score text/file names/identity"
            },ensure_ascii=False,indent=2),encoding="utf-8")
            transfer_path=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}.context_similarity_transfer.json")
            transfer_path.write_text(json.dumps({
                "schema":1,"version":"6.0","memory_path":str(transfer_mem.path),
                "memory_generation":transfer_mem.generation,
                "predictions":[{"context_key":p.get("context_key"),"local_evidence":p.get("local_evidence"),
                                "transfer_evidence":p.get("transfer_evidence"),"transfer_confidence":p.get("transfer_confidence"),
                                "transfer_donors":p.get("transfer_donors"),"transfer_detail":p.get("transfer_detail"),
                                "reason":p.get("reason")} for p in utility_predictions],
                "audit_edge_updates":transfer_events,
                "hard_isolation":{"same_section_character_only":True,"dimension_overlap_required":True,
                                  "transfer_only_top1_forbidden":True,"donor_audit_risk_blocks":True},
                "privacy":"aggregate transfer calibration only; no audio/MIDI/score text/file names/identity"
            },ensure_ascii=False,indent=2),encoding="utf-8")
            archetype_path=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}.performance_archetype_memory.json")
            archetype_path.write_text(json.dumps({
                "schema":1,"version":"6.0","memory_path":str(archetype_mem.path),
                "memory_generation":archetype_mem.generation,
                "classification":comp["archetype"].as_dict(),
                "predictions":[{"context_key":p.get("context_key"),
                                "mixture_confidence":p.get("mixture_confidence"),
                                "mixture_evidence":p.get("mixture_evidence"),
                                "mixture_components":p.get("mixture_components"),
                                "mixture_detail":p.get("mixture_detail"),
                                "reason":p.get("reason")} for p in utility_predictions],
                "updates":archetype_updates,"audit_edge_updates":archetype_audit_events,
                "hard_isolation":{"mixture_only_top1_forbidden":True,
                                  "actual_render_only_learning":True,
                                  "low_mixture_confidence_blocks":True},
                "privacy":"aggregate archetype/control statistics only; no audio/MIDI/score text/file names/note sequences/identity"
            },ensure_ascii=False,indent=2),encoding="utf-8")

            mixture_path=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}.archetype_mixture_memory.json")
            mixture_path.write_text(json.dumps({
                "schema":1,"version":"6.0","memory_path":str(mixture_mem.path),
                "memory_generation":mixture_mem.generation,
                "classification":comp["archetype_mixture"].as_dict(),
                "predictions":[{"context_key":p.get("context_key"),"mixture_confidence":p.get("mixture_confidence"),
                                "mixture_evidence":p.get("mixture_evidence"),"mixture_components":p.get("mixture_components"),
                                "mixture_detail":p.get("mixture_detail"),"reason":p.get("reason")}
                               for p in utility_predictions],
                "audit_component_updates":mixture_audit_events,
                "hard_isolation":{"mixture_only_top1_forbidden":True,
                                  "actual_render_only_learning":True,
                                  "component_edge_audit_calibration":True,
                                  "v58_archetype_trust_not_mutated":True,
                                  "v57_transfer_edges_not_mutated":True},
                "privacy":"component-to-context aggregate calibration only; no audio/MIDI/score text/file names/note sequences/song identity"
            },ensure_ascii=False,indent=2),encoding="utf-8")

            locked_decisions,coherence,intent_report,conductor_search=choose_conductor_locked_decisions_v53(
                comp["graph"],comp["candidate_graphs"],decisions,comp["conductor_intent"]
            )
            conductor_path=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}.conductor_lock.json")
            conductor_path.write_text(json.dumps({
                "schema":1,"version":"5.3","search":conductor_search,
                "intent":comp["conductor_intent"].as_dict(),
                "local_winners":[{"window_id":d["window_id"],"winner":d["winner"]} for d in decisions],
                "selected":[{"window_id":d["window_id"],"winner":d["winner"],
                             "local_winner":d.get("local_winner",d["winner"]),
                             "conductor_section_id":d.get("conductor_section_id"),
                             "conductor_character":d.get("conductor_character"),
                             "conductor_override":bool(d.get("conductor_override",False))}
                            for d in (locked_decisions or [])],
                "global_coherence":coherence.as_dict(),
                "conductor_intent_report":intent_report.as_dict(),
            },ensure_ascii=False,indent=2),encoding="utf-8")

            if locked_decisions is None:
                row,qfull,paths,learned=_full_fallback_round(
                    score,out_dir,qpath,host,port,sample_rate,chunk_seconds,overlap_seconds,
                    round_index,"conductor_intent_lock:"+intent_report.reason)
                row.update({"round":round_index,"plan":plan.as_dict(),
                            "local_decisions_before_fallback":decisions,
                            "global_coherence":coherence.as_dict(),
                            "conductor_intent":comp["conductor_intent"].as_dict(),
                            "conductor_intent_report":intent_report.as_dict(),
                            "conductor_search":conductor_search})
                trace.append(row)
                if not learned:
                    midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row["winner"]]["midi"],
                                         paths[row["winner"]],"REVIEW_BEST")
                    final={"status":"review_required","mode":"full_fallback_conductor_intent",
                           "round":round_index,"reason":row["learning"]["reason"],
                           "winner":row["winner"],"midi":str(midi),"wav":str(wav),"margin":row["margin"]}
                    break
                if round_index>=max_round:
                    midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row["winner"]]["midi"],
                                         paths[row["winner"]],"WINNER")
                    final={"status":"round_cap","mode":"full_fallback_conductor_intent",
                           "round":round_index,"winner":row["winner"],
                           "midi":str(midi),"wav":str(wav),"margin":row["margin"]}
                    break
                continue

            decisions=locked_decisions
            merged=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}_SELECTIVE_MERGED.mid")
            splice_midi_windows_v51(midis["D"],{s:midis[s] for s in "ABC"},decisions,merged)
            last_merged=merged

            # Only learn a global repair policy when the local decisions have a dominant strategy.
            agg=_aggregate_local_learning(decisions)
            mem=RepairPolicyMemoryV49(q["policy_path"]);before=mem.snapshot()
            stale=(before.generation!=int(q["policy_generation"]) or before.profile_hash!=str(q["policy_hash"]))
            if stale:
                learn={"learned":False,"reason":"stale_policy"}
            elif agg.get("accepted"):
                learn=mem.learn(agg["winner"],agg["margin"],agg["safety"],agg["overall"])
            else:
                learn={"learned":False,"reason":agg.get("reason","mixed_local_winners")}
            after=mem.snapshot()

            # Estimate compute relative to four whole-song renders. D's compiled length is the
            # reference; final merged full render is intentionally deferred until convergence.
            _,song_frames,_=compiled_midi_to_shadow_events_v50(midis["D"],sample_rate,tail_seconds=1.5)
            equiv=local_cost_frames/max(1,float(song_frames))
            row={
                "round":round_index,"mode":"selective","plan":plan.as_dict(),
                "archetype_label":comp["archetype"].label,
                "archetype_classification":comp["archetype"].as_dict(),
                "archetype_sidecar":str(comp["archetype_json"]),
                "decisions":decisions,"merged_midi":str(merged),
                "global_coherence":coherence.as_dict(),
                "conductor_steering":{
                    "intent_hash":comp["steering_report"].intent_hash,
                    "sidecar":str(comp["steering_json"]),
                    "candidate_renders_skipped":candidate_renders_skipped,
                    "candidate_renders_escalated":candidate_renders_escalated,
                },
                "conductor_intent":comp["conductor_intent"].as_dict(),
                "conductor_intent_report":intent_report.as_dict(),
                "conductor_search":conductor_search,
                "conductor_lock_json":str(conductor_path),
                "candidate_renders_skipped":candidate_renders_skipped,
                "candidate_renders_escalated":candidate_renders_escalated,
                "candidate_renders_audited":candidate_renders_audited,
                "counterfactual_audit_events":audit_events,
                "counterfactual_audit_memory":audit_mem.snapshot(),
                "counterfactual_audit_sidecar":str(audit_path),
                "context_similarity_transfer_sidecar":str(transfer_path),
                "context_similarity_transfer_memory":str(transfer_mem.path),
                "context_similarity_transfer_generation":transfer_mem.generation,
                "context_similarity_transfer_events":transfer_events,
                "performance_archetype_memory_sidecar":str(archetype_path),
                "performance_archetype_memory":str(archetype_mem.path),
                "performance_archetype_generation":archetype_mem.generation,
                "performance_archetype_updates":archetype_updates,
                "performance_archetype_audit_events":archetype_audit_events,
                "archetype_mixture_sidecar":str(mixture_path),
                "archetype_mixture_memory":str(mixture_mem.path),
                "archetype_mixture_generation":mixture_mem.generation,
                "archetype_mixture_audit_events":mixture_audit_events,
                "candidate_utility_sidecar":str(utility_path),
                "candidate_utility_memory":str(utility_mem.path),
                "candidate_utility_memory_generation":utility_mem.generation,
                "candidate_generation_sidecar":str(comp["steering_json"]),
                "evidence_transaction":evidence_commit,
                "evidence_store_head":evidence_store.head,
                "evidence_store_status":evidence_store.status(),
                "local_render_equivalent_full":round(equiv,6),
                "vs_four_full_render_fraction":round(equiv/4.0,6),
                "aggregate_policy_evidence":agg,
                "learning":{"accepted":bool(learn.get("learned")),"reason":learn.get("reason")},
                "policy_before":{"generation":before.generation,"hash":before.profile_hash,"values":before.values},
                "policy_after":{"generation":after.generation,"hash":after.profile_hash,"values":after.values},
            }
            trace.append(row)

            if learn.get("learned") and round_index<max_round:
                continue

            # Converged/mixed/round-cap: full-pair verification.
            # Render merged + D Original and judge each against its own MIDI. This catches
            # local improvements that produce a worse whole-song result.
            merged_wav=merged.with_suffix(".wav")
            finfo=render_midi_v50(merged,merged_wav,host,port,sample_rate,chunk_seconds,overlap_seconds,
                                  request_seed=5590000+round_index*100)
            d_verify=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v60_R{round_index}_D_GLOBAL_VERIFY.wav")
            dinfo=render_midi_v50(midis["D"],d_verify,host,port,sample_rate,chunk_seconds,overlap_seconds,
                                  request_seed=5595000+round_index*100)
            pair_audio,pair_sr,pair_frames=load_render_set_v49([merged_wav,d_verify])
            mev=midi_to_judge_events_v49(merged,pair_sr,pair_frames)
            dev=midi_to_judge_events_v49(midis["D"],pair_sr,pair_frames)
            mscore=judge_take(pair_audio[0],pair_sr,mev,0,pair_frames)
            dscore=judge_take(pair_audio[1],pair_sr,dev,0,pair_frames)
            pair_delta=float(mscore.overall-dscore.overall)
            pair_safety_delta=float(mscore.safety-dscore.safety)
            pair_pass=(pair_delta>=-.025 and pair_safety_delta>=-.04)

            if not pair_pass:
                row2,qfull,paths,learned2=_full_fallback_round(
                    score,out_dir,qpath,host,port,sample_rate,chunk_seconds,overlap_seconds,
                    round_index,"global_pair_verify_failed")
                row2.update({"round":round_index,"plan":plan.as_dict(),
                             "global_coherence":coherence.as_dict(),
                             "conductor_intent":comp["conductor_intent"].as_dict(),
                             "conductor_intent_report":intent_report.as_dict(),
                             "conductor_search":conductor_search,
                             "pair_verify":{
                                 "passed":False,"merged":score_dict(mscore),"D":score_dict(dscore),
                                 "overall_delta":pair_delta,"safety_delta":pair_safety_delta}})
                trace.append(row2)
                label="WINNER" if row2["margin"]>=MIN_MARGIN else "REVIEW_BEST"
                midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row2["winner"]]["midi"],
                                     paths[row2["winner"]],label)
                final={"status":"global_pair_fallback","mode":"full_fallback_pair_verify",
                       "round":round_index,"winner":row2["winner"],"midi":str(midi),"wav":str(wav),
                       "margin":row2["margin"],"pair_overall_delta":pair_delta,
                       "pair_safety_delta":pair_safety_delta}
                break

            label="WINNER" if learn.get("learned") or all(d["margin"]>=MIN_MARGIN for d in decisions) else "REVIEW_BEST"
            fm,fw=_copy_final(score,out_dir,merged,merged_wav,label)
            final={
                "status":"round_cap" if round_index>=max_round and learn.get("learned") else "selective_converged",
                "mode":"selective_conductor_lock","round":round_index,
                "window_winners":[{"window_id":d["window_id"],"winner":d["winner"],
                                   "local_winner":d.get("local_winner",d["winner"]),
                                   "coherence_override":bool(d.get("coherence_override",False)),
                                   "conductor_override":bool(d.get("conductor_override",False)),
                                   "conductor_section_id":d.get("conductor_section_id"),
                                   "conductor_character":d.get("conductor_character"),
                                   "margin":d["margin"]} for d in decisions],
                "global_coherence":coherence.as_dict(),
                "conductor_intent":comp["conductor_intent"].as_dict(),
                "conductor_intent_report":intent_report.as_dict(),
                "pair_verify":{"passed":True,"merged":score_dict(mscore),"D":score_dict(dscore),
                               "overall_delta":pair_delta,"safety_delta":pair_safety_delta},
                "midi":str(fm),"wav":str(fw),
                "full_final_render":{k:(str(v) if isinstance(v,Path) else v) for k,v in finfo.items()},
                "full_D_verify_render":{k:(str(v) if isinstance(v,Path) else v) for k,v in dinfo.items()},
                "local_render_equivalent_full":round(equiv,6),
                "estimated_total_vs_four_full_fraction":round((equiv+2.0)/4.0,6),
            }
            break

        if final is None:
            final={"status":"internal_no_final"}
    finally:
        if spawned is not None:
            try:spawned.terminate();spawned.wait(timeout=4)
            except Exception:
                try:spawned.kill()
                except Exception:pass

    report={
        "schema":1,"version":"6.0","source_score":str(score),"out_dir":str(out_dir.resolve()),
        "service":{"host":host,"port":int(port),"backend":backend,"mock":bool(mock)},
        "selective_settings":{"max_windows":int(max_windows),"coverage_limit":float(coverage_limit),
                              "local_context":float(local_context),"max_local_context_seconds":float(max_local_context_seconds)},
        "max_round":max_round,"sample_rate":int(sample_rate),
        "elapsed_seconds":round(time.time()-start,3),"rounds":trace,"final":final,
        "counterfactual_auditor":{"memory_path":str(audit_mem.path),"generation":audit_mem.generation,
                                   "base_interval":12,"false_prune_margin":.025,
                                   "per_context_disable":True,"recovery_clean_audits":4},
        "context_similarity_transfer":{"memory_path":str(transfer_mem.path),"generation":transfer_mem.generation,
                                       "same_section_character_only":True,"min_jaccard":.34,
                                       "transfer_only_top1_forbidden":True,"edge_specific_audit_calibration":True},
        "cross_song_performance_archetype":{
            "memory_path":str(archetype_mem.path),"generation":archetype_mem.generation,
            "control_profile_only":True,"archetype_only_top1_forbidden":True,
            "actual_render_only_learning":True,
            "labels":["intimate","ballad","dramatic","chamber","cinematic"]},
        "soft_archetype_mixture":{
            "memory_path":str(mixture_mem.path),"generation":mixture_mem.generation,
            "max_components":3,"min_component_weight":.08,
            "mixture_only_top1_forbidden":True,"component_edge_audit_calibration":True},
        "unified_evidence_store":{
            "path":str(evidence_store.path),"bootstrap":evidence_bootstrap,
            "status":evidence_store.status(),"transactional_namespaces":5,
            "content_addressed":True,"compressed_blobs":True,
            "crash_drift_recovery":True,"legacy_json_compatible":True},
        "authority_note":"v6.0 does not blend the five evidence algorithms. It transactionally governs v5.5 Utility, v5.6 Audit, v5.7 Similarity, v5.8 Archetype and v5.9 Mixture namespaces with content-addressed snapshots, rollback, quarantine and export. Existing Audio Judge and all musical safety guards remain authoritative.",
    }
    rp=out_dir/(score.stem+"_SONICRAFT_STRINGS_v60_DECISION_TRACE.json")
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report,rp

def main(argv=None):
    ap=argparse.ArgumentParser(description="SONICRAFT v6.0 Unified Evidence Store / Memory Consolidation auto-loop.")
    ap.add_argument("score",type=Path);ap.add_argument("--out-dir",type=Path);ap.add_argument("--policy",type=Path)
    ap.add_argument("--host",default="127.0.0.1");ap.add_argument("--port",type=int,default=49337)
    ap.add_argument("--backend",choices=["auto","torch","ort"],default="auto")
    ap.add_argument("--model-dir",type=Path);ap.add_argument("--cache-dir",type=Path);ap.add_argument("--mock",action="store_true")
    ap.add_argument("--max-round",type=int,default=6);ap.add_argument("--sample-rate",type=int,default=48000)
    ap.add_argument("--chunk-seconds",type=float,default=40.0);ap.add_argument("--overlap-seconds",type=float,default=.75)
    ap.add_argument("--max-windows",type=int,default=6);ap.add_argument("--coverage-limit",type=float,default=.55)
    ap.add_argument("--local-context",type=float,default=.85);ap.add_argument("--max-local-context-seconds",type=float,default=28.0)
    ap.add_argument("--utility-memory",type=Path,default=None)
    ap.add_argument("--audit-memory",type=Path,default=None)
    ap.add_argument("--transfer-memory",type=Path,default=None)
    ap.add_argument("--archetype-memory",type=Path,default=None)
    ap.add_argument("--mixture-memory",type=Path,default=None)
    ap.add_argument("--evidence-store",type=Path,default=None)
    a=ap.parse_args(argv)
    try:
        r,rp=run_auto_loop_v60(a.score,a.out_dir,a.policy,a.host,a.port,a.backend,a.model_dir,a.cache_dir,
                               a.mock,a.max_round,a.sample_rate,a.chunk_seconds,a.overlap_seconds,
                               a.max_windows,a.coverage_limit,a.local_context,a.max_local_context_seconds,
                               a.utility_memory,a.audit_memory,a.transfer_memory,a.archetype_memory,a.mixture_memory,
                               a.evidence_store)
    except Exception as ex:
        print("ERROR:",ex,file=sys.stderr);return 2
    print("SONICRAFT v6.0 Unified Evidence Store Auto-Loop finished")
    print("Final:",json.dumps(r["final"],ensure_ascii=False))
    print("Decision trace:",rp)
    return 0 if r["final"].get("status") not in ("render_failed","internal_no_final") else 3

if __name__=="__main__":raise SystemExit(main())
