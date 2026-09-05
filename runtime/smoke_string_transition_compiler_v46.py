from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v46 import compile_file
from compile_midi_performance_v29 import parse_midi
XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="88"/></direction>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="stop"/><glissando type="start"/></notations></note>\n<note><rest/><duration>4</duration></note>\n<note><pitch><step>F</step><octave>5</octave></pitch><duration>4</duration><notations><articulations><staccato/></articulations></notations></note>\n</measure></part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"transition.musicxml";src.write_text(XML)
    out,sj,cj,ej,gj,tj,g,cr,er,links=compile_file(src)
    assert all(p.exists() for p in [out,sj,cj,ej,gj,tj])
    tdct=json.loads(tj.read_text());sd=json.loads(sj.read_text())
    assert sd["sonicraft_version"]=="4.6"
    assert tdct["link_count"]==1,tdct
    assert tdct["links"][0]["explicit_portamento"] is True
    assert sd["continuous_transition"]["new_midi_cc_or_paramids"] is False
    assert g.notes[0].transition_out_link_id==g.notes[1].transition_in_link_id==1
    assert g.notes[2].transition_in_link_id==0
    fmt,ppq,tracks=parse_midi(out)
    assert fmt==1 and ppq==960 and len(tracks)==5
    cc38=[]
    for e in tracks[1]:
        if e.status<0xF0 and (e.status&0xF0)==0xB0 and e.data[0]==38:
            cc38.append(e.data[1])
    # Linked A->E shares one window; detached F opens its own window.
    assert sum(1 for v in cc38 if v==0)==2,cc38
    assert sum(1 for v in cc38 if v>0)>=3,cc38
print("SONICRAFT v4.6 transition compiler smoke OK",len(links),cc38)
