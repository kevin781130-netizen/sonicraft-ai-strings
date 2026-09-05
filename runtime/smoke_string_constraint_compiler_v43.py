from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v43 import compile_file
from compile_midi_performance_v29 import parse_midi
XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>\n<direction><sound tempo="120"/></direction>\n<note><pitch><step>D</step><octave>4</octave></pitch><duration>8</duration><notations><slur type="start"/></notations></note>\n<note><chord/><pitch><step>A</step><octave>4</octave></pitch><duration>8</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>E</step><octave>5</octave></pitch><duration>8</duration><notations><slur type="stop"/></notations></note>\n<note><chord/><pitch><step>G</step><octave>5</octave></pitch><duration>8</duration></note>\n<note><chord/><pitch><step>B</step><octave>5</octave></pitch><duration>8</duration></note>\n<note><chord/><pitch><step>D</step><octave>6</octave></pitch><duration>8</duration></note>\n<note><chord/><pitch><step>F</step><octave>6</octave></pitch><duration>8</duration></note>\n</measure></part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"constraint.musicxml";src.write_text(XML)
    out,sj,cj,g,r=compile_file(src)
    assert out.exists() and sj.exists() and cj.exists()
    d=json.loads(sj.read_text());c=json.loads(cj.read_text())
    assert d["sonicraft_version"]=="4.3"
    assert "constraint_solver" in d
    assert len(c["simultaneous_groups"])>=2
    ds=next(x for x in c["simultaneous_groups"] if x["note_count"]==2)
    assert ds["double_stop_feasible"] and ds["performance_mode"]=="double_stop"
    assert any("double_stop_consolidated" in n["constraint_flags"] for n in d["notes"][:2])
    assert d["notes"][0]["divisi_desk"]==d["notes"][1]["divisi_desk"]
    assert d["notes"][0]["string_index"]!=d["notes"][1]["string_index"]
    assert any(x["note_count"]>4 and x["divisi_required"] for x in c["simultaneous_groups"])
    fmt,ppq,tracks=parse_midi(out)
    assert fmt==1 and ppq==960 and len(tracks)==5
    # Conductor must carry at least one SONICRAFT marker meta event for the overload.
    marker=False
    raw=out.read_bytes()
    assert b"SONICRAFT ERROR" in raw
print("SONICRAFT v4.3 constraint compiler/DAW marker smoke OK")
