from pathlib import Path
import tempfile,wave,json,math
import numpy as np
from compile_musicxml_strings_v49 import compile_file
from midi_judge_adapter_v49 import midi_to_judge_events_v49
from iterate_strings_v49 import iterate_v49

XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="90"/></direction>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>\n</measure></part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'

def write_wav(path,x,sr=48000):
    x=np.clip(np.asarray(x,np.float32),-1,1)
    pcm=(x*32767).astype("<i2")
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr)
        w.writeframes(np.repeat(pcm[:,None],2,axis=1).tobytes())

with tempfile.TemporaryDirectory() as td:
    td=Path(td);score=td/"loop.musicxml";score.write_text(XML)
    policy=td/"policy.json"
    r=compile_file(score,policy_path=policy,round_index=1)
    q=json.loads(r["judge_queue_json"].read_text())
    sr=48000;frames=int(sr*3.2);t=np.arange(frames,dtype=np.float32)/sr

    # Generate B from its own note onsets: stable tone + modest onset energy.
    ev=midi_to_judge_events_v49(r["midi_B"],sr,frames)
    ons=[e["project_sample"] for e in ev if e["type"]==1 and 0<=e["project_sample"]<frames]
    b=.12*np.sin(2*np.pi*220*t)
    for o in ons:
        n=min(frames-o,int(.08*sr))
        if n>0:b[o:o+n]+=.10*np.exp(-np.arange(n)/(sr*.024))*np.sin(2*np.pi*330*np.arange(n)/sr)
    # A = broadband chatter, C = aggressive AM, D = clipped square.
    rng=np.random.default_rng(7)
    a=.04*np.sin(2*np.pi*220*t)+.32*rng.standard_normal(frames)
    c=.22*np.sign(np.sin(2*np.pi*220*t))*np.sign(np.sin(2*np.pi*37*t))
    d=np.clip(1.25*np.sign(np.sin(2*np.pi*220*t)), -1.0,1.0)
    waves={"A":a,"B":b,"C":c,"D":d}
    render=td/"renders";render.mkdir()
    for slot,x in waves.items():
        expected=q["slots"][slot]["expected_render"]
        write_wav(render/expected,x,sr)

    report,rp=iterate_v49(r["judge_queue_json"],render)
    assert report["audio_judge"]["winner"]=="B",report["audio_judge"]
    assert report["learning"]["accepted"],report["learning"]
    assert report["policy_after"]["generation"]==1
    assert report["next_round"]["generated"]
    nq=Path(report["next_round"]["judge_queue"]);assert nq.exists()
    q2=json.loads(nq.read_text())
    assert q2["round_index"]==2 and q2["policy_generation"]==1
    assert q2["policy_hash"]==report["policy_after"]["hash"]
    # Replaying the old R1 render after policy generation advanced must be stale and cannot learn again.
    stale,_=iterate_v49(r["judge_queue_json"],render,no_regenerate=True)
    assert not stale["learning"]["accepted"] and stale["learning"]["reason"]=="stale_policy",stale["learning"]
    assert stale["policy_after"]["generation"]==1
    print("SONICRAFT v4.9 end-to-end Judge->learn->R2 + stale replay gate OK",report["audio_judge"]["winner"],round(report["audio_judge"]["margin"],4),q2["policy_values"])
