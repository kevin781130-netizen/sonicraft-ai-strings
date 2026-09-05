from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v50 import compile_file
from shadow_render_auto_v50 import compiled_midi_to_shadow_events_v50,start_shadow_service_v50,render_midi_v50

XML='''<?xml version="1.0"?>
<score-partwise version="4.0"><part-list>
<score-part id="P1"><part-name>Violin 1</part-name></score-part><score-part id="P2"><part-name>Violin 2</part-name></score-part><score-part id="P3"><part-name>Viola</part-name></score-part><score-part id="P4"><part-name>Cello</part-name></score-part>
</part-list>
<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="84"/></direction>
<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>
<note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>
<note><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>
<note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note></measure></part>
<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>
<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>
<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>
</score-partwise>'''
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/'shadow.musicxml';src.write_text(XML);policy=td/'policy.json'
    r=compile_file(src,policy_path=policy)
    ev,end,bpm=compiled_midi_to_shadow_events_v50(r['midi_B'])
    codes={e['note'] for e in ev if e['type']==4}
    assert 0 in codes and 112 in codes and 118 in codes and 120 in codes and 121 in codes and 122 in codes,codes
    assert any(e['type']==1 for e in ev) and any(e['type']==2 for e in ev)
    port=49550;proc=None
    try:
        proc,status=start_shadow_service_v50(port=port,mock=True,cache_dir=td/'cache')
        rr=render_midi_v50(r['midi_B'],td/'B.wav',port=port,chunk_seconds=5.0,overlap_seconds=.2)
        assert rr['frames']>48000 and rr['peak']>0 and rr['events']==len(ev)
        assert (td/'B.wav').exists()
    finally:
        if proc is not None:
            proc.terminate();proc.wait(timeout=3)
print('SONICRAFT v5.0 compiled MIDI -> Shadow events -> mock service WAV smoke OK',len(ev),end,round(bpm,2))
