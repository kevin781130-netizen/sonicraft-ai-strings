from __future__ import annotations
import argparse, csv, math
from pathlib import Path
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

TPB=480
KS_BASE=24
ART={'sustain':0,'legato':1,'portamento':2,'expressive':3,'marcato':4,'staccato':5,'spiccato':6,'tremolo':7,'pizzicato':8,'trill':9,'harmonic':10,'flautando':11}
PARTS={
    'VlnI': {'name':'Violin I','lo':55,'hi':88,'anchors':[60,64,67,72,76,79,84]},
    'VlnII':{'name':'Violin II','lo':55,'hi':84,'anchors':[59,62,67,71,74,79]},
    'Viola':{'name':'Viola','lo':48,'hi':79,'anchors':[52,55,60,64,67,72,76]},
    'Cello':{'name':'Cello','lo':36,'hi':67,'anchors':[40,43,48,52,55,60,64]},
}
DYN={'pp':28,'mp':48,'mf':70,'f':96,'ff':116}

def abs_to_track(events, bpm=68, name='Cue'):
    tr=MidiTrack(); tr.append(MetaMessage('track_name',name=name,time=0)); tr.append(MetaMessage('set_tempo',tempo=bpm2tempo(bpm),time=0))
    events=sorted(events,key=lambda x:(x[0],x[1]))
    last=0
    for tick,order,msg in events:
        msg.time=max(0,tick-last); tr.append(msg); last=tick
    return tr

def ev_cc(events,tick,cc,val,ch=0): events.append((tick,1,Message('control_change',channel=ch,control=cc,value=max(0,min(127,int(val))),time=0)))
def ev_note(events,start,end,note,vel=70,ch=0):
    events.append((start,5,Message('note_on',channel=ch,note=note,velocity=vel,time=0)))
    events.append((end,0,Message('note_off',channel=ch,note=note,velocity=0,time=0)))
def ev_ks(events,tick,art,ch=0):
    n=KS_BASE+ART[art]; events.append((tick,1,Message('note_on',channel=ch,note=n,velocity=1,time=0))); events.append((tick+30,0,Message('note_off',channel=ch,note=n,velocity=0,time=0)))
def ev_marker(events,tick,text): events.append((tick,2,MetaMessage('marker',text=text,time=0)))

def save(path,events,bpm,name):
    mid=MidiFile(ticks_per_beat=TPB); mid.tracks.append(abs_to_track(events,bpm,name)); path.parent.mkdir(parents=True,exist_ok=True); mid.save(path)

def legato_file(part,out,rows):
    spec=PARTS[part]; events=[]; tick=0; bpm=64
    ev_ks(events,0,'legato')
    for dyn in ('mp','mf','f'):
        for anchor in spec['anchors']:
            for interval in (-12,-7,-5,-4,-3,-2,-1,1,2,3,4,5,7,12):
                target=anchor+interval
                if not(spec['lo']<=target<=spec['hi']): continue
                ev_marker(events,tick,f"{spec['name']} LEGATO {interval:+d}st {dyn} natural-vibrato")
                ev_cc(events,tick,1,DYN[dyn]);ev_cc(events,tick,3,62);ev_cc(events,tick,11,112)
                # 120 ms-ish overlap at 64 BPM, represented symbolically; musician should connect naturally.
                ev_note(events,tick,tick+TPB*2,anchor,DYN[dyn])
                ev_note(events,tick+TPB*2-70,tick+TPB*4-70,target,DYN[dyn])
                rows.append([part,'legato',dyn,anchor,target,interval,tick/TPB,'connect naturally; preserve bow/finger noise'])
                tick += TPB*5
    save(out/f'{part}_01_legato_intervals.mid',events,bpm,f'{spec["name"]} Legato Intervals')

def portamento_file(part,out,rows):
    spec=PARTS[part];events=[];tick=0;bpm=60;ev_ks(events,0,'portamento')
    intervals=(-12,-9,-7,-5,-4,-3,3,4,5,7,9,12)
    anchors=spec['anchors'][1:-1] or spec['anchors']
    for dyn in ('mp','mf'):
        for anchor in anchors:
            for interval in intervals:
                target=anchor+interval
                if not(spec['lo']<=target<=spec['hi']):continue
                ev_marker(events,tick,f'{spec["name"]} PORTAMENTO {interval:+d} {dyn} restrained')
                ev_cc(events,tick,1,DYN[dyn]);ev_cc(events,tick,3,58);ev_cc(events,tick,11,112)
                ev_note(events,tick,tick+TPB*2,anchor,DYN[dyn]);ev_note(events,tick+TPB*2-90,tick+TPB*4-90,target,DYN[dyn])
                rows.append([part,'portamento',dyn,anchor,target,interval,tick/TPB,'restrained Mandarin-ballad slide; do not exaggerate'])
                tick+=TPB*5
    save(out/f'{part}_02_portamento.mid',events,bpm,f'{spec["name"]} Portamento')

def dynamics_file(part,out,rows):
    spec=PARTS[part];events=[];tick=0;bpm=64;ev_ks(events,0,'expressive')
    notes=spec['anchors'][::2]
    for note in notes:
        for mode in ('crescendo','diminuendo','delayed_vibrato','no_vibrato'):
            ev_marker(events,tick,f'{spec["name"]} {mode} note={note}')
            ev_cc(events,tick,11,112)
            if mode=='crescendo':
                for i in range(9):ev_cc(events,tick+i*TPB//2,1,24+i*11);ev_cc(events,tick+i*TPB//2,3,52+i*3)
            elif mode=='diminuendo':
                for i in range(9):ev_cc(events,tick+i*TPB//2,1,112-i*10);ev_cc(events,tick+i*TPB//2,3,76-i*3)
            elif mode=='delayed_vibrato':
                ev_cc(events,tick,1,66);ev_cc(events,tick,3,0);ev_cc(events,tick+TPB,3,20);ev_cc(events,tick+TPB*2,3,55);ev_cc(events,tick+TPB*3,3,70)
            else:
                ev_cc(events,tick,1,60);ev_cc(events,tick,3,0)
            ev_note(events,tick,tick+TPB*4,note,70)
            rows.append([part,mode,'curve',note,note,0,tick/TPB,'hold 4 beats; follow CC curve musically'])
            tick+=TPB*5
    save(out/f'{part}_03_dynamics_vibrato.mid',events,bpm,f'{spec["name"]} Dynamics Vibrato')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='datasets/recording_cues/mandarin_ballad_q4');a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for part in PARTS:
        legato_file(part,out,rows);portamento_file(part,out,rows);dynamics_file(part,out,rows)
    with (out/'session_plan.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['part','exercise','dynamic','source_note','target_note','interval_semitones','start_beat','instruction']);w.writerows(rows)
    (out/'README.txt').write_text(
        'SONICRAFT Mandarin Ballad Q4 recording cue pack\n'
        'These MIDI files are original procedural training cues, not copied melodies.\n'
        'Treat CC1/CC3/CC11 as musical instructions, not robotic automation.\n'
        'Record 24-bit/96-kHz masters and preserve player/take IDs.\n'
        'A signed commercial ML/model-weight rights release is required before any take enters a release model.\n',encoding='utf-8')
    print('recording cue pack:',out,'rows:',len(rows))
if __name__=='__main__':main()
