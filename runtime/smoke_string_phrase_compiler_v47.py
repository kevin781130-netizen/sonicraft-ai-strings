from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v47 import compile_file
from compile_midi_performance_v29 import parse_midi
XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="90"/></direction>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>\n</measure></part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"phrase.musicxml";src.write_text(XML)
    out,sj,cj,ej,gj,tj,pj,g,cr,er,links,arcs=compile_file(src)
    assert all(p.exists() for p in [out,sj,cj,ej,gj,tj,pj])
    sd=json.loads(sj.read_text());pd=json.loads(pj.read_text())
    assert sd["sonicraft_version"]=="4.7"
    assert sd["phrase_longline"]["phrase_count"]==1
    assert sd["phrase_longline"]["new_midi_cc_or_paramids"] is False
    assert pd["phrase_count"]==1 and pd["sentinel_cc38_norm"]>0
    assert len(links)==3 and len(arcs)==1
    fmt,ppq,tracks=parse_midi(out)
    assert fmt==1 and ppq==960 and len(tracks)==5
    cc38=[]
    for e in tracks[1]:
        if e.status<0xF0 and (e.status&0xF0)==0xB0 and e.data[0]==38:
            cc38.append(e.data[1])
    assert 1 in cc38,cc38
    assert cc38.count(0)==1,cc38
    assert max(cc38)>=64
print("SONICRAFT v4.7 phrase compiler/sentinel smoke OK",len(links),cc38[:8])
