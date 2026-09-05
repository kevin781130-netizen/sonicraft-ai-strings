"""Dependency-free MusicXML -> SONICRAFT event JSON converter.

Preserves note timing, tempo, basic dynamics and common string articulations. It is intentionally
conservative: unsupported notation is reported instead of guessed.
"""
from __future__ import annotations
import argparse,json,re,xml.etree.ElementTree as ET
from pathlib import Path
ART={'staccato':5,'tenuto':0,'accent':4,'strong-accent':4,'trill-mark':9,'tremolo':7,'harmonic':10,'pizzicato':8,'spiccato':6,'portamento':2,'glissando':2,'slur':1}
DYN={'ppp':.16,'pp':.24,'p':.34,'mp':.46,'mf':.60,'f':.74,'ff':.86,'fff':.95}
STEP={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}

def _tag(x):return x.split('}')[-1]
def _child(el,name):return next((c for c in el if _tag(c.tag)==name),None)
def _text(el,name,default=None):
    c=_child(el,name);return c.text if c is not None and c.text is not None else default

def convert_musicxml(path, sample_rate=48000, default_bpm=120.0):
    root=ET.parse(path).getroot();events=[];warnings=[];part_index=0
    for part in [x for x in root.iter() if _tag(x.tag)=='part']:
        divisions=1; bpm=float(default_bpm); sec_pos=0.0; dyn=.60; last_on_sec=None; part_idx=min(3,part_index);part_index+=1
        for measure in [x for x in part if _tag(x.tag)=='measure']:
            for el in measure:
                tg=_tag(el.tag)
                if tg=='attributes':
                    d=_text(el,'divisions'); divisions=max(1,int(float(d))) if d else divisions
                elif tg=='direction':
                    for c in el.iter():
                        ct=_tag(c.tag)
                        if ct=='sound' and c.get('tempo'): bpm=float(c.get('tempo'))
                        if ct in DYN: dyn=DYN[ct]
                elif tg=='backup': sec_pos-=float(_text(el,'duration','0'))/divisions*60.0/max(1e-6,bpm)
                elif tg=='forward': sec_pos+=float(_text(el,'duration','0'))/divisions*60.0/max(1e-6,bpm)
                elif tg=='note':
                    dur=float(_text(el,'duration','0'))/divisions; chord=_child(el,'chord') is not None; rest=_child(el,'rest') is not None
                    dur_sec=dur*60.0/max(1e-6,bpm); onsec=last_on_sec if chord and last_on_sec is not None else sec_pos
                    if not rest:
                        pitch=_child(el,'pitch')
                        if pitch is not None:
                            step=_text(pitch,'step','C');octv=int(_text(pitch,'octave','4'));alt=int(float(_text(pitch,'alter','0')))
                            midi=max(0,min(127,12*(octv+1)+STEP.get(step,0)+alt))
                            art=0
                            for n in el.iter():
                                nt=_tag(n.tag)
                                if nt in ART: art=ART[nt]
                                if nt=='technical':
                                    txt=' '.join((z.text or '') for z in n.iter()).lower()
                                    if 'pizz' in txt:art=8
                                    if 'harmonic' in txt:art=10
                            on=int(round(onsec*sample_rate));off=int(round((onsec+dur_sec)*sample_rate))
                            ctrl=[dyn,.5,.9,.86,.5,1.,1.,.18,.5,art/11.0,.5,.5,.38,0.]
                            events.append({'project_sample':on,'type':1,'part':part_idx,'note':midi,'articulation':art,'velocity':dyn,'tempo_bpm':bpm,'controls':ctrl})
                            events.append({'project_sample':off,'type':2,'part':part_idx,'note':midi,'articulation':art,'velocity':0.0,'tempo_bpm':bpm,'controls':ctrl})
                            last_on_sec=onsec
                    if not chord: sec_pos+=dur_sec
    events.sort(key=lambda e:(e['project_sample'],e['type']))
    return {'format':'sonicraft_event_json_v1','sample_rate':int(sample_rate),'events':events,'warnings':warnings}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');ap.add_argument('--sample-rate',type=int,default=48000);ap.add_argument('--bpm',type=float,default=120.0);a=ap.parse_args()
    out=convert_musicxml(a.input,a.sample_rate,a.bpm);Path(a.output).write_text(json.dumps(out,indent=2),encoding='utf-8');print(f"wrote {len(out['events'])} events -> {a.output}")
if __name__=='__main__':main()
