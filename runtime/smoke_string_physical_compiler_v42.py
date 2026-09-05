from __future__ import annotations
from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v42 import compile_file
from compile_midi_performance_v29 import parse_midi

XML="""<?xml version="1.0"?>
<score-partwise version="4.0">
<part-list>
<score-part id="P1"><part-name>Violin 1</part-name></score-part>
<score-part id="P2"><part-name>Violin 2</part-name></score-part>
<score-part id="P3"><part-name>Viola</part-name></score-part>
<score-part id="P4"><part-name>Cello</part-name></score-part>
</part-list>
<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
<direction><sound tempo="84"/><direction-type><dynamics><mf/></dynamics></direction-type></direction>
<note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><notations><articulations><staccato/></articulations><technical><down-bow/></technical></notations></note>
<note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>
<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>
<note><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><notations><glissando type="start"/></notations></note>
</measure></part>
<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>
<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>
<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>
</score-partwise>"""

with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"phys.musicxml";src.write_text(XML)
    out,j,g=compile_file(src)
    d=json.loads(j.read_text())
    assert d["sonicraft_version"]=="4.2"
    assert d["physical_performance_graph"]["planner"]
    assert len(d["physical_notes"])==4
    assert d["physical_notes"][0]["open_string"] is True
    assert d["physical_notes"][0]["bow_direction"]=="down"
    assert d["physical_notes"][-1]["portamento_route"]==1.0
    fmt,ppq,tracks=parse_midi(out)
    assert fmt==1 and ppq==960 and len(tracks)==5
    ccs=set()
    for e in tracks[1]:
        if e.status<0xF0 and (e.status&0xF0)==0xB0: ccs.add(e.data[0])
    assert {21,22,23,24,25,26,27,28,29,30,31,33,34,35}.issubset(ccs),ccs
    assert 32 not in ccs
print("SONICRAFT v4.2 physical MIDI compiler smoke OK")
