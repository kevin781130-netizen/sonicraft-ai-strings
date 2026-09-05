from pathlib import Path
import tempfile,math
import numpy as np
import auto_loop_strings_v51 as loop
from shadow_render_auto_v50 import compiled_midi_to_shadow_events_v50
from shadow_render_selective_v51 import tick_window_to_samples_v51

XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="90"/></direction>\n<note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>E</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="continue"/><glissando type="start"/></notations></note>\n<note><pitch><step>A</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>D</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>\n</measure>\n<measure number="2"><note><rest/><duration>8</duration></note>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note></measure>\n</part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'

def fake_local(midi,start_tick,end_tick,out_wav=None,host="127.0.0.1",port=0,sample_rate=8000,
               preroll=.4,postroll=.4,request_id=1,max_context_seconds=20):
    events,end_sample,bpm=compiled_midi_to_shadow_events_v50(midi,sample_rate,tail_seconds=.4)
    a,b=tick_window_to_samples_v51(midi,start_tick,end_tick,sample_rate)
    b=min(b,end_sample);n=max(64,b-a)
    t=np.arange(n,dtype=np.float32)/sample_rate
    name=Path(midi).name
    if "_REPAIR_B_" in name:
        x=.12*np.sin(2*np.pi*220*t)
        # Add modest authored onset energy so B scores cleanly.
        for e in events:
            if e["type"]==1 and a<=e["project_sample"]<b:
                o=e["project_sample"]-a;m=min(n-o,int(.06*sample_rate))
                if m>0:x[o:o+m]+=.08*np.exp(-np.arange(m)/(sample_rate*.02))*np.sin(2*np.pi*330*np.arange(m)/sample_rate)
    elif "_REPAIR_A_" in name:
        rng=np.random.default_rng(4);x=.03*np.sin(2*np.pi*220*t)+.28*rng.standard_normal(n)
    elif "_REPAIR_C_" in name:
        x=.22*np.sign(np.sin(2*np.pi*220*t))*np.sign(np.sin(2*np.pi*31*t))
    else:
        x=np.clip(1.1*np.sign(np.sin(2*np.pi*220*t)),-1,1)
    audio=np.repeat(np.asarray(x,np.float32)[:,None],2,axis=1)
    marker=0.9 if "_REPAIR_B_" in name else (0.2 if "_REPAIR_A_" in name else (0.1 if "_REPAIR_C_" in name else 0.3))
    audio[0,0]=marker
    if out_wav is not None:
        import soundfile as sf;sf.write(str(out_wav),audio,sample_rate,subtype="FLOAT")
    return {"audio":audio,"events":events,"core_start_sample":a,"core_end_sample":b,
             "render_start_sample":a,"render_end_sample":b,"sample_rate":sample_rate,
             "frames":n,"context_frames":n+int((preroll+postroll)*sample_rate),
             "context_seconds":n/sample_rate+preroll+postroll,"wav":Path(out_wav) if out_wav else None,
             "peak":float(np.max(np.abs(audio))),"service_status":0}

from audio_take_judge_v37 import TakeJudgeScore
def fake_judge(audio,sample_rate,events,start_sample,end_sample):
    marker=float(audio[0,0])
    overall=max(0.05,min(.95,marker))
    return TakeJudgeScore(overall,overall,overall,overall,overall,.92,float(np.max(np.abs(audio))))

with tempfile.TemporaryDirectory() as td:
    td=Path(td);score=td/"sel.musicxml";score.write_text(XML)
    original=loop.render_midi_window_v51
    original_judge=loop.judge_take
    loop.render_midi_window_v51=fake_local
    loop.judge_take=fake_judge
    try:
        report,rp=loop.run_auto_loop_v51(score,td/"out",td/"policy.json",port=49581,mock=True,max_round=1,
                                         sample_rate=8000,coverage_limit=.55,local_context=.4,
                                         max_local_context_seconds=12)
    finally:
        loop.render_midi_window_v51=original
        loop.judge_take=original_judge
    assert report["rounds"][0]["mode"]=="selective",report["rounds"][0].get("fallback_reason")
    ds=report["rounds"][0]["decisions"]
    assert ds and all(d["winner"]=="B" for d in ds),[(d["winner"],d["margin"]) for d in ds]
    assert all(d["margin"]>=.025 for d in ds)
    assert report["final"]["mode"]=="selective"
    assert Path(report["final"]["midi"]).exists() and Path(report["final"]["wav"]).exists()
    assert report["rounds"][0]["local_render_equivalent_full"]<4.0
    assert report["final"]["estimated_total_vs_four_full_fraction"]<1.0
    print("SONICRAFT v5.1 selective accepted branch / merge / final render smoke OK",
          [(d["winner"],round(d["margin"],4)) for d in ds],
          round(report["final"]["estimated_total_vs_four_full_fraction"],3))
