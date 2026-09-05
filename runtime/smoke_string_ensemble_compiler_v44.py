from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v44 import compile_file
from compile_midi_performance_v29 import parse_midi
XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="120"/></direction><note><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><notations><technical><down-bow/></technical><articulations><accent/></articulations></notations></note><note><pitch><step>F</step><octave>5</octave></pitch><duration>4</duration></note></measure></part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><articulations><accent/></articulations></notations></note><note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><notations><articulations><accent/></articulations></notations></note><note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>D</step><octave>3</octave></pitch><duration>4</duration><notations><articulations><accent/></articulations></notations></note><note><pitch><step>E</step><octave>3</octave></pitch><duration>4</duration></note></measure></part>\n</score-partwise>'
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"ensemble.musicxml";src.write_text(XML)
    out,sj,cj,ej,g,cr,er=compile_file(src)
    assert all(p.exists() for p in [out,sj,cj,ej])
    d=json.loads(sj.read_text());e=json.loads(ej.read_text())
    assert d["sonicraft_version"]=="4.4"
    assert d["ensemble_coordination"]["hq_timing_bus"]["36"]
    assert e["coordinated_attacks"]>=8
    fmt,ppq,tracks=parse_midi(out)
    assert fmt==1 and ppq==960 and len(tracks)==5
    ccs=set()
    for tr in tracks[1:]:
        for x in tr:
            if x.status<0xF0 and (x.status&0xF0)==0xB0:ccs.add(x.data[0])
    assert 36 in ccs and 37 in ccs
print("SONICRAFT v4.4 ensemble compiler smoke OK",er.coordinated_attacks,er.phrase_breaths)
