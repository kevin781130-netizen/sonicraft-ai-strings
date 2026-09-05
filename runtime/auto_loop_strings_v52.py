"""SONICRAFT v5.2 Global Performance Coherence Guard Auto-Loop.

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

from compile_musicxml_strings_v52 import compile_file
from string_performance_critic_v48 import evaluate_performance_v48
from selective_phrase_search_v51 import build_selective_plan_v51
from shadow_render_selective_v51 import render_midi_window_v51,tick_window_to_samples_v51
from selective_midi_merge_v51 import splice_midi_windows_v51
from global_performance_coherence_v52 import choose_coherent_decisions_v52
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
    mo=out_dir/f"{stem}_SONICRAFT_STRINGS_v52_{label}.mid"
    wo=out_dir/f"{stem}_SONICRAFT_STRINGS_v52_{label}.wav"
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

def run_auto_loop_v52(score,out_dir=None,policy_path=None,host="127.0.0.1",port=49337,
                      backend="auto",model_dir=None,cache_dir=None,mock=False,max_round=MAX_ROUND,
                      sample_rate=48000,chunk_seconds=40.0,overlap_seconds=.75,max_windows=6,
                      coverage_limit=.55,local_context=.85,max_local_context_seconds=28.0):
    score=Path(score).resolve()
    if not score.exists():raise FileNotFoundError(score)
    out_dir=Path(out_dir) if out_dir else score.with_name(score.stem+"_SONICRAFT_v52_SELECTIVE")
    out_dir.mkdir(parents=True,exist_ok=True)
    max_round=max(1,min(MAX_ROUND,int(max_round)))
    spawned=None;trace=[];final=None;start=time.time()
    last_merged=None
    try:
        spawned,_=start_shadow_service_v50(host,port,mock,backend,model_dir,cache_dir)
        for round_index in range(1,max_round+1):
            out=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v52_R{round_index}.mid")
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

            for wi,w in enumerate(plan.windows):
                slot_results={};scores={}
                for si,slot in enumerate(SLOTS):
                    lwav=local_dir/f"W{w.window_id:02d}_{slot}.wav"
                    r=render_midi_window_v51(
                        midis[slot],w.start_tick,w.end_tick,lwav,host,port,sample_rate,
                        preroll=local_context,postroll=local_context,
                        request_id=5510000+round_index*10000+wi*100+si*10,
                        max_context_seconds=max_local_context_seconds
                    )
                    slot_results[slot]=r
                    local_cost_frames+=int(r["context_frames"])
                    scores[slot]=judge_take(r["audio"],sample_rate,r["events"],
                                            r["core_start_sample"],r["core_end_sample"])
                rank=sorted(SLOTS,key=lambda s:scores[s].overall,reverse=True)
                winner,runner=rank[:2];margin=float(scores[winner].overall-scores[runner].overall)
                ws=scores[winner]
                d={
                    "window_id":w.window_id,"start_tick":w.start_tick,"end_tick":w.end_tick,
                    "phrase_keys":w.phrase_keys,"dimensions":w.dimensions,"priority":w.priority,
                    "winner":winner,"runner_up":runner,"margin":round(margin,9),
                    "duration_seconds":slot_results[winner]["frames"]/float(sample_rate),
                    "scores":{s:score_dict(scores[s]) for s in SLOTS},
                    "local_wavs":{s:str(slot_results[s]["wav"]) for s in SLOTS},
                    "context_seconds":slot_results[winner]["context_seconds"],
                }
                decisions.append(d)
                if margin<MIN_MARGIN:low_conf=f"local_low_margin_W{w.window_id}"
                elif ws.safety<SAFETY_FLOOR:low_conf=f"local_safety_floor_W{w.window_id}"
                elif ws.overall<OVERALL_FLOOR:low_conf=f"local_low_overall_W{w.window_id}"
                if low_conf:break

            if low_conf:
                # Local ambiguity means the window assumption is not trusted. Fall back to the
                # proven whole-song A/B/C/D Judge for this round.
                row,qfull,paths,learned=_full_fallback_round(
                    score,out_dir,qpath,host,port,sample_rate,chunk_seconds,overlap_seconds,
                    round_index,low_conf)
                row.update({"round":round_index,"plan":plan.as_dict(),
                            "local_decisions_before_fallback":decisions,
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

            coherent_decisions,coherence,coherence_search=choose_coherent_decisions_v52(
                comp["graph"],comp["candidate_graphs"],decisions
            )
            coherence_path=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v52_R{round_index}.global_coherence.json")
            coherence_path.write_text(json.dumps({
                "schema":1,"version":"5.2","search":coherence_search,
                "local_winners":[{"window_id":d["window_id"],"winner":d["winner"]} for d in decisions],
                "selected":[{"window_id":d["window_id"],"winner":d["winner"],
                             "local_winner":d.get("local_winner",d["winner"]),
                             "coherence_override":bool(d.get("coherence_override",False))}
                            for d in (coherent_decisions or [])],
                "coherence":coherence.as_dict(),
            },ensure_ascii=False,indent=2),encoding="utf-8")

            if coherent_decisions is None:
                row,qfull,paths,learned=_full_fallback_round(
                    score,out_dir,qpath,host,port,sample_rate,chunk_seconds,overlap_seconds,
                    round_index,"global_coherence:"+coherence.reason)
                row.update({"round":round_index,"plan":plan.as_dict(),
                            "local_decisions_before_fallback":decisions,
                            "global_coherence":coherence.as_dict(),
                            "coherence_search":coherence_search})
                trace.append(row)
                if not learned:
                    midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row["winner"]]["midi"],
                                         paths[row["winner"]],"REVIEW_BEST")
                    final={"status":"review_required","mode":"full_fallback_global_coherence",
                           "round":round_index,"reason":row["learning"]["reason"],
                           "winner":row["winner"],"midi":str(midi),"wav":str(wav),"margin":row["margin"]}
                    break
                if round_index>=max_round:
                    midi,wav=_copy_final(score,out_dir,out_dir/qfull["slots"][row["winner"]]["midi"],
                                         paths[row["winner"]],"WINNER")
                    final={"status":"round_cap","mode":"full_fallback_global_coherence",
                           "round":round_index,"winner":row["winner"],
                           "midi":str(midi),"wav":str(wav),"margin":row["margin"]}
                    break
                continue

            decisions=coherent_decisions
            merged=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v52_R{round_index}_SELECTIVE_MERGED.mid")
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
                "decisions":decisions,"merged_midi":str(merged),
                "global_coherence":coherence.as_dict(),"coherence_search":coherence_search,
                "global_coherence_json":str(coherence_path),
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
            d_verify=out_dir/(score.stem+f"_SONICRAFT_STRINGS_v52_R{round_index}_D_GLOBAL_VERIFY.wav")
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
                             "coherence_search":coherence_search,
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
                "mode":"selective_global_guard","round":round_index,
                "window_winners":[{"window_id":d["window_id"],"winner":d["winner"],
                                   "local_winner":d.get("local_winner",d["winner"]),
                                   "coherence_override":bool(d.get("coherence_override",False)),
                                   "margin":d["margin"]} for d in decisions],
                "global_coherence":coherence.as_dict(),
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
        "schema":1,"version":"5.1","source_score":str(score),"out_dir":str(out_dir.resolve()),
        "service":{"host":host,"port":int(port),"backend":backend,"mock":bool(mock)},
        "selective_settings":{"max_windows":int(max_windows),"coverage_limit":float(coverage_limit),
                              "local_context":float(local_context),"max_local_context_seconds":float(max_local_context_seconds)},
        "max_round":max_round,"sample_rate":int(sample_rate),
        "elapsed_seconds":round(time.time()-start,3),"rounds":trace,"final":final,
        "authority_note":"Local Audio Judge proposes repairs; Global Coherence Guard can substitute a near-scoring candidate or D. Final merged-vs-D full pair verification protects whole-song audio behavior.",
    }
    rp=out_dir/(score.stem+"_SONICRAFT_STRINGS_v52_DECISION_TRACE.json")
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report,rp

def main(argv=None):
    ap=argparse.ArgumentParser(description="SONICRAFT v5.2 Global Performance Coherence Guard auto-loop.")
    ap.add_argument("score",type=Path);ap.add_argument("--out-dir",type=Path);ap.add_argument("--policy",type=Path)
    ap.add_argument("--host",default="127.0.0.1");ap.add_argument("--port",type=int,default=49337)
    ap.add_argument("--backend",choices=["auto","torch","ort"],default="auto")
    ap.add_argument("--model-dir",type=Path);ap.add_argument("--cache-dir",type=Path);ap.add_argument("--mock",action="store_true")
    ap.add_argument("--max-round",type=int,default=6);ap.add_argument("--sample-rate",type=int,default=48000)
    ap.add_argument("--chunk-seconds",type=float,default=40.0);ap.add_argument("--overlap-seconds",type=float,default=.75)
    ap.add_argument("--max-windows",type=int,default=6);ap.add_argument("--coverage-limit",type=float,default=.55)
    ap.add_argument("--local-context",type=float,default=.85);ap.add_argument("--max-local-context-seconds",type=float,default=28.0)
    a=ap.parse_args(argv)
    try:
        r,rp=run_auto_loop_v52(a.score,a.out_dir,a.policy,a.host,a.port,a.backend,a.model_dir,a.cache_dir,
                               a.mock,a.max_round,a.sample_rate,a.chunk_seconds,a.overlap_seconds,
                               a.max_windows,a.coverage_limit,a.local_context,a.max_local_context_seconds)
    except Exception as ex:
        print("ERROR:",ex,file=sys.stderr);return 2
    print("SONICRAFT v5.2 Global Performance Coherence Guard Auto-Loop finished")
    print("Final:",json.dumps(r["final"],ensure_ascii=False))
    print("Decision trace:",rp)
    return 0 if r["final"].get("status") not in ("render_failed","internal_no_final") else 3

if __name__=="__main__":raise SystemExit(main())
