from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v45 import compile_file
from compile_midi_performance_v29 import parse_midi
XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list><score-part id="P1"><part-name>Violin 1</part-name></score-part><score-part id="P2"><part-name>Violin 2</part-name></score-part><score-part id="P3"><part-name>Viola</part-name></score-part><score-part id="P4"><part-name>Cello</part-name></score-part></part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="72"/><direction-type><dynamics><mf/></dynamics></direction-type></direction><note><pitch><step>E</step><octave>5</octave></pitch><duration>16</duration><notations><slur type="start"/><articulations><accent/></articulations></notations></note></measure></part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>A</step><octave>4</octave></pitch><duration>16</duration><notations><slur type="start"/></notations></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>D</step><octave>4</octave></pitch><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>D</step><octave>3</octave></pitch><duration>16</duration></note></measure></part>\n</score-partwise>'
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"g.musicxml";src.write_text(XML)
    out,sj,cj,ej,gj,g,cr,er=compile_file(src)
    assert all(p.exists() for p in [out,sj,cj,ej,gj])
    d=json.loads(sj.read_text());gg=json.loads(gj.read_text())
    assert d["sonicraft_version"]=="4.5"
    assert d["continuous_gesture"]["hq_interpolation"] is True
    assert len(gg["gesture_notes"])>=3
    assert all(len(x["anchors"])==7 for x in gg["gesture_notes"])
    fmt,ppq,tracks=parse_midi(out)
    assert fmt==1 and ppq==960 and len(tracks)==5
    ccs=[]
    for tr in tracks[1:]:
        for e in tr:
            if e.status<0xF0 and (e.status&0xF0)==0xB0:ccs.append(e.data[0])
    assert 38 in ccs and 39 in ccs
    assert ccs.count(31)>=7 and ccs.count(33)>=7 and ccs.count(39)>=7
print("SONICRAFT v4.5 gesture compiler smoke OK")
