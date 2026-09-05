from pathlib import Path
import tempfile,json
from auto_loop_strings_v50 import run_auto_loop_v50

XML='''<?xml version="1.0"?>
<score-partwise version="4.0"><part-list>
<score-part id="P1"><part-name>Violin 1</part-name></score-part><score-part id="P2"><part-name>Violin 2</part-name></score-part><score-part id="P3"><part-name>Viola</part-name></score-part><score-part id="P4"><part-name>Cello</part-name></score-part>
</part-list><part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="92"/></direction>
<note><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>
<note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>
<note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>
<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note></measure></part>
<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>
<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part>
<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part></score-partwise>'''
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/'loop.musicxml';src.write_text(XML);out=td/'auto';policy=td/'policy.json'
    report,rp=run_auto_loop_v50(src,out,policy,port=49551,mock=True,max_round=2,chunk_seconds=5,overlap_seconds=.2,cache_dir=td/'cache')
    assert rp.exists() and report['rounds']
    assert report['final']['status'] in ('review_required','round_cap')
    assert len(report['rounds'])<=2
    last=report['rounds'][-1]
    assert set(last['scores'])==set('ABCD')
    assert all(Path(last['renders'][s]['wav']).exists() for s in 'ABCD')
    final=report['final'];assert Path(final.get('midi')).exists() and Path(final.get('wav')).exists()
print('SONICRAFT v5.0 fully automatic mock Shadow render/Judge/stop/winner-artifact smoke OK',report['final']['status'],len(report['rounds']))
