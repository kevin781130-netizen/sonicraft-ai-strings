from pathlib import Path
import tempfile,json
import numpy as np
import auto_loop_strings_v58 as loop
from compile_musicxml_strings_v58 import compile_file as real_compile
from shadow_render_auto_v50 import compiled_midi_to_shadow_events_v50
from shadow_render_selective_v51 import tick_window_to_samples_v51
from audio_take_judge_v37 import TakeJudgeScore
from string_performance_critic_v48 import evaluate_performance_v48
from selective_phrase_search_v51 import build_selective_plan_v51
from candidate_utility_predictor_v55 import CandidateUtilityMemoryV55,context_key_v55
from context_similarity_transfer_v57 import SimilarityTransferMemoryV57
from counterfactual_auditor_v56 import CounterfactualAuditMemoryV56
from performance_archetype_memory_v58 import PerformanceArchetypeMemoryV58,ArchetypeClassificationV58,predict_candidate_utility_v58

XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="90"/></direction>\n<note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>E</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="continue"/><glissando type="start"/></notations></note>\n<note><pitch><step>A</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>D</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>\n</measure>\n<measure number="2"><note><rest/><duration>8</duration></note>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note></measure>\n</part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'

def _write(path,audio,sr):
    import soundfile as sf
    sf.write(str(path),np.asarray(audio,np.float32),sr,subtype="FLOAT")

def fake_local(midi,start_tick,end_tick,out_wav=None,host="127.0.0.1",port=0,sample_rate=8000,
               preroll=.4,postroll=.4,request_id=1,max_context_seconds=20):
    events,end_sample,bpm=compiled_midi_to_shadow_events_v50(midi,sample_rate,tail_seconds=.4)
    a,b=tick_window_to_samples_v51(midi,start_tick,end_tick,sample_rate)
    b=min(b,end_sample);n=max(64,b-a);t=np.arange(n,dtype=np.float32)/sample_rate
    name=Path(midi).name
    marker=.90 if "_REPAIR_B_" in name else (.96 if "_REPAIR_A_" in name else (.76 if "_REPAIR_C_" in name else .64))
    x=.07*np.sin(2*np.pi*220*t)
    audio=np.repeat(x[:,None],2,axis=1);audio[0,0]=marker
    if out_wav is not None:_write(out_wav,audio,sample_rate)
    return {"audio":audio,"events":events,"core_start_sample":a,"core_end_sample":b,
             "render_start_sample":a,"render_end_sample":b,"sample_rate":sample_rate,
             "frames":n,"context_frames":n+int((preroll+postroll)*sample_rate),
             "context_seconds":n/sample_rate+preroll+postroll,"wav":Path(out_wav) if out_wav else None,
             "peak":float(np.max(np.abs(audio))),"service_status":0}

def fake_full(midi,out_wav,host="127.0.0.1",port=0,sample_rate=8000,chunk_seconds=40,overlap_seconds=.75,request_seed=1,**kwargs):
    n=24000;t=np.arange(n,dtype=np.float32)/sample_rate
    marker=.84 if "SELECTIVE_MERGED" in Path(midi).name else .80
    x=.06*np.sin(2*np.pi*220*t);audio=np.repeat(x[:,None],2,axis=1);audio[0,0]=marker
    _write(out_wav,audio,sample_rate)
    return {"wav":Path(out_wav),"sample_rate":sample_rate,"frames":n,"chunks":1,
             "peak":float(np.max(np.abs(audio))),"cache_hits":0}

def fake_judge(audio,sample_rate,events,start_sample,end_sample):
    marker=float(audio[0,0]);overall=max(.05,min(.95,marker))
    return TakeJudgeScore(overall,overall,overall,overall,overall,.92,float(np.max(np.abs(audio))))

with tempfile.TemporaryDirectory() as td:
    td=Path(td);score=td/"archetype_cross_song.musicxml";score.write_text(XML)
    utility=td/"utility.json";audit=td/"audit.json";transfer=td/"transfer.json";archp=td/"archetype_memory.json"
    pre=real_compile(score,td/"pre.mid",td/"pre_policy.json",1)
    _,issues=evaluate_performance_v48(pre["graph"])
    plan=build_selective_plan_v51(pre["graph"],issues,pre["reports"],max_windows=6,coverage_limit=.55)
    assert plan.selective and plan.windows
    w0=plan.windows[0]
    fake_budget={"section_id":2,"character":"build","active":["A","B","C","D"],"deferred":[],"progressive":False}
    core_dims=[d for d in w0.dimensions if d in ("bow_reserve","transition","vibrato","dynamics_arc","gesture_spikes","ensemble_alignment","latent_playability")]
    target=context_key_v55("build",core_dims)
    cls=ArchetypeClassificationV58(
        "intimate",.82,"ballad",.28,
        {"dynamic":.44,"contrast":.18,"vibrato":.35,"rate":.47,"bow":.44,"desk":.31,"transition":.36,"role_focus":.58},
        {"intimate":.10,"ballad":.31,"chamber":.42,"cinematic":.55,"dramatic":.67},
        "prototype_match"
    )
    um=CandidateUtilityMemoryV55(utility);am=CounterfactualAuditMemoryV56(audit)
    tm=SimilarityTransferMemoryV57(transfer);arm=PerformanceArchetypeMemoryV58(archp)
    hist={"B":{"overall":.94,"safety":.93},"C":{"overall":.80,"safety":.90},"D":{"overall":.65,"safety":.94}}
    for _ in range(16):
        rr=arm.learn_rendered(cls.label,target,hist,"B",cls.confidence,full_evidence=False)
        assert rr["learned"]
    assert not um.context(target)
    assert "A" not in arm.context(cls.label,target).get("slots",{})
    pred0=predict_candidate_utility_v58(
        "build",core_dims,pre.get("steered_scores"),pre.get("reports"),
        pre["policy_snapshot"].values,um,am,tm,arm,cls,fake_budget["active"]
    )
    assert pred0.reason=="archetype_cross_song_top2_plus_D",pred0
    assert "A" in pred0.pruned_slots,pred0
    for i in range(11):
        pp=am.plan(pred0,fake_budget["active"])
        assert not pp.audit_due,(i,pp)

    # Force only the classifier confidence for this integration fixture; all actual score/candidate
    # generation remains the real v5.8 compiler path.
    def wrapped_compile(*args,**kwargs):
        r=real_compile(*args,**kwargs)
        r["archetype"]=cls
        payload={"schema":1,"version":"5.8","classification":cls.as_dict(),
                 "privacy_note":"synthetic integration fixture"}
        r["archetype_json"].write_text(json.dumps(payload,indent=2))
        return r

    o_compile=loop.compile_file;o_budget=loop.render_slots_for_window_v54
    o_local,o_judge,o_full=loop.render_midi_window_v51,loop.judge_take,loop.render_midi_v50
    loop.compile_file=wrapped_compile
    loop.render_slots_for_window_v54=lambda intent,a,b:dict(fake_budget)
    loop.render_midi_window_v51=fake_local;loop.judge_take=fake_judge;loop.render_midi_v50=fake_full
    try:
        report,rp=loop.run_auto_loop_v58(
            score,td/"out",td/"policy.json",port=49598,mock=True,max_round=1,
            sample_rate=8000,coverage_limit=.55,local_context=.4,max_local_context_seconds=12,
            utility_memory_path=utility,audit_memory_path=audit,transfer_memory_path=transfer,
            archetype_memory_path=archp
        )
    finally:
        loop.compile_file=o_compile;loop.render_slots_for_window_v54=o_budget
        loop.render_midi_window_v51=o_local;loop.judge_take=o_judge;loop.render_midi_v50=o_full

    row=report["rounds"][0];d0=row["decisions"][0];cb=d0["candidate_budget"]
    assert row["mode"]=="selective",row
    assert cb["utility_reason"]=="archetype_cross_song_top2_plus_D",cb
    assert cb["local_utility_evidence"]==0 and cb["transferred_utility_evidence"]==0,cb
    assert cb["archetype_evidence"]>=1.5,cb
    assert cb["counterfactual_audit"] is True,cb
    assert cb["standard_escalation"] is False,cb
    assert set(cb["rendered_slots"])==set("ABCD"),cb
    assert row["counterfactual_audit_events"],row
    ev=row["counterfactual_audit_events"][0]
    assert ev["false_prune"] is True and ev["preaudit_winner"]=="B" and ev["full_winner"]=="A",ev
    assert ev["counterfactual_gain"]>=.05,ev
    assert row["performance_archetype_audit_events"],row
    aev=row["performance_archetype_audit_events"][0]
    assert aev["false_prune"] is True,aev
    cal=PerformanceArchetypeMemoryV58(archp).calibration(cls.label,target)
    assert cal["trust"]<1.0 and cal["false_prunes"]==1,cal
    # No v5.7 similarity donor existed, so an archetype miss must not fabricate transfer edges.
    assert SimilarityTransferMemoryV57(transfer).edges=={},SimilarityTransferMemoryV57(transfer).snapshot()
    assert d0["winner"]=="A",d0
    assert report["final"]["pair_verify"]["passed"]
    print("SONICRAFT v5.8 ARCHETYPE hidden false-prune audit isolated calibration OK",
          "B->A",ev["counterfactual_gain"],"archetype_trust",cal["trust"],
          "transfer_edges",len(SimilarityTransferMemoryV57(transfer).edges))
