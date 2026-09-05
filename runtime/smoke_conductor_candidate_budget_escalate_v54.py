from pathlib import Path
import tempfile
import numpy as np
import auto_loop_strings_v54 as loop
from shadow_render_auto_v50 import compiled_midi_to_shadow_events_v50
from shadow_render_selective_v51 import tick_window_to_samples_v51
from audio_take_judge_v37 import TakeJudgeScore
XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="90"/></direction>\n<note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>E</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="continue"/><glissando type="start"/></notations></note>\n<note><pitch><step>A</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>D</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>\n</measure>\n<measure number="2"><note><rest/><duration>8</duration></note>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note></measure>\n</part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'


def _write(path,audio,sr):
    import soundfile as sf
    sf.write(str(path),np.asarray(audio,np.float32),sr,subtype="FLOAT")

def fake_local(midi,start_tick,end_tick,out_wav=None,host="127.0.0.1",port=0,sample_rate=8000,
               preroll=.4,postroll=.4,request_id=1,max_context_seconds=20):
    events,end_sample,bpm=compiled_midi_to_shadow_events_v50(midi,sample_rate,tail_seconds=.4)
    a,b=tick_window_to_samples_v51(midi,start_tick,end_tick,sample_rate)
    b=min(b,end_sample);n=max(64,b-a)
    t=np.arange(n,dtype=np.float32)/sample_rate
    name=Path(midi).name
    # The first problem window is Climax: primary B/C/D are intentionally within 0.025;
    # deferred A clearly wins when progressive escalation is triggered.
    marker=.700 if "_REPAIR_B_" in name else (.900 if "_REPAIR_A_" in name else (.695 if "_REPAIR_C_" in name else .690))
    x=.07*np.sin(2*np.pi*220*t)
    audio=np.repeat(x[:,None],2,axis=1);audio[0,0]=marker
    if out_wav is not None:_write(out_wav,audio,sample_rate)
    return {"audio":audio,"events":events,"core_start_sample":a,"core_end_sample":b,
             "render_start_sample":a,"render_end_sample":b,"sample_rate":sample_rate,
             "frames":n,"context_frames":n+int((preroll+postroll)*sample_rate),
             "context_seconds":n/sample_rate+preroll+postroll,"wav":Path(out_wav) if out_wav else None,
             "peak":float(np.max(np.abs(audio))),"service_status":0}

def fake_full(midi,out_wav,host="127.0.0.1",port=0,sample_rate=8000,chunk_seconds=40,overlap_seconds=.75,request_seed=1,**kwargs):
    n=24000
    t=np.arange(n,dtype=np.float32)/sample_rate
    name=Path(midi).name
    marker=.86 if "SELECTIVE_MERGED" in name else .80
    x=.06*np.sin(2*np.pi*220*t)
    audio=np.repeat(x[:,None],2,axis=1);audio[0,0]=marker
    _write(out_wav,audio,sample_rate)
    return {"wav":Path(out_wav),"sample_rate":sample_rate,"frames":n,"chunks":1,
             "peak":float(np.max(np.abs(audio))),"cache_hits":0}

def fake_judge(audio,sample_rate,events,start_sample,end_sample):
    marker=float(audio[0,0]);overall=max(.05,min(.95,marker))
    return TakeJudgeScore(overall,overall,overall,overall,overall,.92,float(np.max(np.abs(audio))))

with tempfile.TemporaryDirectory() as td:
    td=Path(td);score=td/"coherent.musicxml";score.write_text(XML)
    o_local,o_judge,o_full=loop.render_midi_window_v51,loop.judge_take,loop.render_midi_v50
    loop.render_midi_window_v51=fake_local;loop.judge_take=fake_judge;loop.render_midi_v50=fake_full
    try:
        report,rp=loop.run_auto_loop_v54(score,td/"out",td/"policy.json",port=49591,mock=True,max_round=1,
                                         sample_rate=8000,coverage_limit=.55,local_context=.4,
                                         max_local_context_seconds=12)
    finally:
        loop.render_midi_window_v51=o_local;loop.judge_take=o_judge;loop.render_midi_v50=o_full
    row=report["rounds"][0]
    assert row["mode"]=="selective",row
    assert row["global_coherence"]["passed"],row["global_coherence"]
    assert row["conductor_intent_report"]["passed"],row["conductor_intent_report"]
    assert row["conductor_intent"]["intent_hash"]==row["conductor_search"]["intent_hash"]
    assert Path(row["conductor_lock_json"]).exists()
    assert row["candidate_renders_escalated"]>=1,row
    assert any(d["candidate_budget"]["expanded"] for d in row["decisions"]),row["decisions"]
    expanded=[d for d in row["decisions"] if d["candidate_budget"]["expanded"]]
    assert any("A" in d["candidate_budget"]["rendered_slots"] for d in expanded),expanded
    assert any(d["winner"]=="A" for d in expanded),expanded
    assert report["final"]["mode"]=="selective_conductor_lock",report["final"]
    assert report["final"]["pair_verify"]["passed"],report["final"]["pair_verify"]
    assert report["final"]["pair_verify"]["overall_delta"]>0
    assert Path(report["final"]["midi"]).exists() and Path(report["final"]["wav"]).exists()
    print("SONICRAFT v5.4 progressive candidate budget ESCALATION smoke OK",
          row["conductor_search"],report["final"]["pair_verify"]["overall_delta"],
          "intent",row["conductor_intent"]["intent_hash"],
          "cost_fraction",round(report["final"]["estimated_total_vs_four_full_fraction"],3))
