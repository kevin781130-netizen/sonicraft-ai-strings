from pathlib import Path
import tempfile,wave
import numpy as np
import auto_loop_strings_v50 as loop
from midi_judge_adapter_v49 import midi_to_judge_events_v49

XML='''<?xml version="1.0"?><score-partwise version="4.0"><part-list>
<score-part id="P1"><part-name>Violin 1</part-name></score-part><score-part id="P2"><part-name>Violin 2</part-name></score-part><score-part id="P3"><part-name>Viola</part-name></score-part><score-part id="P4"><part-name>Cello</part-name></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="90"/></direction>
<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note><note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note><note><pitch><step>E</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note><note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note></measure></part>
<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part><part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part><part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure></part></score-partwise>'''

def ww(path,x,sr):
    pcm=(np.clip(x,-1,1)*32767).astype('<i2');st=np.repeat(pcm[:,None],2,axis=1)
    with wave.open(str(path),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes(st.tobytes())

def fake_render(midi,out_wav,host,port,sample_rate,chunk_seconds,overlap_seconds,request_seed=0,**kw):
    midi=Path(midi);out_wav=Path(out_wav);sr=16000;frames=int(sr*3.2);t=np.arange(frames,dtype=np.float32)/sr
    name=midi.name
    if '_REPAIR_B_' in name:
        ev=midi_to_judge_events_v49(midi,sr,frames);ons=[e['project_sample'] for e in ev if e['type']==1 and 0<=e['project_sample']<frames]
        x=.12*np.sin(2*np.pi*220*t)
        for o in ons:
            n=min(frames-o,int(.08*sr))
            if n>0:x[o:o+n]+=.10*np.exp(-np.arange(n)/(sr*.024))*np.sin(2*np.pi*330*np.arange(n)/sr)
    elif '_REPAIR_A_' in name:
        rng=np.random.default_rng(11+request_seed);x=.03*np.sin(2*np.pi*220*t)+.30*rng.standard_normal(frames)
    elif '_REPAIR_C_' in name:
        x=.22*np.sign(np.sin(2*np.pi*220*t))*np.sign(np.sin(2*np.pi*37*t))
    else:
        x=np.sign(np.sin(2*np.pi*220*t))
    ww(out_wav,x,sr)
    return {'wav':out_wav,'frames':frames,'sample_rate':sr,'chunks':1,'peak':float(np.max(np.abs(x))),'events':1}

with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/'accept.musicxml';src.write_text(XML);out=td/'auto';policy=td/'policy.json'
    old_start,old_render=loop.start_shadow_service_v50,loop.render_midi_v50
    loop.start_shadow_service_v50=lambda *a,**k:(None,{'reachable':True,'ready':True,'flags':8})
    loop.render_midi_v50=fake_render
    try:report,rp=loop.run_auto_loop_v50(src,out,policy,max_round=2,sample_rate=16000)
    finally:loop.start_shadow_service_v50,loop.render_midi_v50=old_start,old_render
    assert len(report['rounds'])==2,report
    assert report['rounds'][0]['audio_winner']=='B' and report['rounds'][0]['learning']['accepted']
    assert report['rounds'][1]['audio_winner']=='B' and report['rounds'][1]['learning']['accepted']
    assert report['final']['status']=='round_cap' and report['final']['winner']=='B',report['final']
    assert Path(report['final']['midi']).name.endswith('_WINNER.mid') and Path(report['final']['wav']).name.endswith('_WINNER.wav')
    assert Path(report['final']['midi']).exists() and Path(report['final']['wav']).exists() and rp.exists()
print('SONICRAFT v5.0 accepted R1->R2->WINNER orchestration smoke OK',report['final']['winner'],len(report['rounds']))
