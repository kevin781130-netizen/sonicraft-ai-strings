from pathlib import Path
import tempfile,zipfile,json
from compile_musicxml_strings_v41 import compile_file
from compile_midi_performance_v29 import parse_midi

XML='<?xml version="1.0" encoding="UTF-8"?>\n<score-partwise version="4.0">\n<part-list><score-part id="P1"><part-name>Violin 1</part-name></score-part><score-part id="P2"><part-name>Violin 2</part-name></score-part><score-part id="P3"><part-name>Viola</part-name></score-part><score-part id="P4"><part-name>Cello</part-name></score-part></part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><key><fifths>2</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time></attributes>\n<direction><sound tempo="96"/><direction-type><dynamics><mf/></dynamics></direction-type></direction>\n<note><pitch><step>C</step><octave>5</octave></pitch><duration>16</duration><voice>1</voice><notations><ornaments><tremolo>3</tremolo></ornaments><articulations><accent/></articulations></notations></note>\n<note><chord/><pitch><step>E</step><octave>5</octave></pitch><duration>16</duration><voice>2</voice><notations><articulations><tenuto/></articulations></notations></note>\n<note><chord/><pitch><step>G</step><octave>5</octave></pitch><duration>16</duration><voice>3</voice><notations><slur type="start"/></notations></note>\n<note><chord/><pitch><step>B</step><octave>5</octave></pitch><duration>16</duration><voice>4</voice><notations><articulations><accent/><tenuto/></articulations></notations></note>\n<note><chord/><pitch><step>D</step><octave>6</octave></pitch><duration>16</duration><voice>5</voice><notations><technical><up-bow/></technical></notations></note>\n<direction><direction-type><words>col legno</words></direction-type></direction>\n</measure><measure number="2"><direction><sound tempo="120"/></direction><attributes><time><beats>3</beats><beat-type>4</beat-type></time></attributes>\n<note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><tie type="start"/><notations><tied type="start"/></notations></note>\n<note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><tie type="stop"/><notations><tied type="stop"/></notations></note>\n</measure></part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    src=td/"test.musicxml";src.write_text(XML,encoding="utf-8")
    out,j,g=compile_file(src)
    data=json.loads(j.read_text(encoding="utf-8"))
    assert data["ppq"]==960 and len(data["notes"])==6, (data["ppq"],len(data["notes"]))
    assert any(w["type"]=="string_voice_lane_overflow" for w in data["warnings"])
    assert any(w["type"]=="unsupported_string_technique" for w in data["warnings"])
    assert data["tempos"][0]["bpm"]==96 and data["tempos"][-1]["bpm"]==120
    assert any(x["numerator"]==3 for x in data["time_signatures"])
    assert data["key_signatures"][0]["fifths"]==2
    first5=data["notes"][:5]
    channels={n["lane_channel"] for n in first5}
    assert {0,4,5,6}.issubset(channels), channels
    assert any(n["base_art"]==7 and (n["stack"]&1) for n in first5)
    assert any(n["stack"]&4 for n in first5)
    fmt,div,tracks=parse_midi(out)
    assert fmt==1 and div==960 and len(tracks)==5
    ccs=set();chs=set()
    for e in tracks[1]:
        if e.status<0xF0:
            hi=e.status&0xF0;ch=e.status&0x0F
            if hi==0xB0:ccs.add(e.data[0]);chs.add(ch)
            elif hi in (0x80,0x90):chs.add(ch)
    assert set(range(21,27)).issubset(ccs)
    assert {0,4,5,6}.issubset(chs)
    mxl=td/"test.mxl"
    container_xml='<?xml version="1.0"?><container><rootfiles><rootfile full-path="score.musicxml"/></rootfiles></container>'
    with zipfile.ZipFile(mxl,"w") as z:
        z.writestr("META-INF/container.xml",container_xml)
        z.writestr("score.musicxml",XML)
    _,_,gm=compile_file(mxl,td/"mxl.mid",td/"mxl.score.json")
    assert len(gm.notes)==len(g.notes)
print("SONICRAFT v4.1 strings score/voice-lane smoke OK")
