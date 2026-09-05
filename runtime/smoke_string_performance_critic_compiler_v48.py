from pathlib import Path
import tempfile,json,hashlib
from compile_musicxml_strings_v48 import compile_file
from compile_midi_performance_v29 import parse_midi
XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="88"/></direction>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>\n</measure></part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"critic.musicxml";src.write_text(XML)
    r=compile_file(src)
    for k in ["midi_A","midi_B","midi_C","midi_D","critic_json","judge_queue_json","score_json"]:
        assert r[k].exists(),(k,r[k])
    q=json.loads(r["judge_queue_json"].read_text())
    c=json.loads(r["critic_json"].read_text())
    s=json.loads(r["score_json"].read_text())
    assert q["slots"]["D"]["label"]=="Original"
    assert set(q["slots"])==set("ABCD")
    assert c["critic_scope"].startswith("score/performance")
    assert c["final_authority"].startswith("render A/B/C/D")
    assert s["sonicraft_version"]=="4.8"
    assert s["performance_critic"]["audio_judge_required_for_final_winner"] is True
    # All four are valid type-1, PPQ960, 5-track MIDI and are explicitly retagged v4.8.
    for key in ["midi_A","midi_B","midi_C","midi_D"]:
        fmt,ppq,tracks=parse_midi(r[key]);assert fmt==1 and ppq==960 and len(tracks)==5
        assert b"v4.8" in r[key].read_bytes()
    # At least repair strategy C should differ bytewise from D even when the source is already clean.
    assert hashlib.sha256(r["midi_C"].read_bytes()).digest()!=hashlib.sha256(r["midi_D"].read_bytes()).digest()
print("SONICRAFT v4.8 compiler A/B/C/D + judge queue smoke OK",r["recommended"])
