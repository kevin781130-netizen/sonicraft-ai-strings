from __future__ import annotations
import argparse,math,random
from pathlib import Path
from mido import MidiFile,MidiTrack,Message,MetaMessage,bpm2tempo

# Copyright-clean procedural Mandarin-pop ballad curriculum. No song melodies are copied.
PROGS=[(0,7,9,5),(9,5,0,7),(0,4,5,7),(0,9,5,7),(5,7,4,9)] # scale-degree semitone roots relative to tonic
KEYS=[48,50,51,53,55,56,57,58]  # C3..Bb3 root region
KS=24
ART={'sustain':0,'legato':1,'portamento':2,'expressive':3,'marcato':4,'staccato':5,'spiccato':6,'tremolo':7,'pizzicato':8,'trill':9,'harmonic':10,'flautando':11}

def add_cc(track,cc,val,time=0,ch=0):track.append(Message('control_change',channel=ch,control=cc,value=max(0,min(127,int(val))),time=time))
def add_note(track,n,dur,ch=0,vel=70,time=0):track.append(Message('note_on',channel=ch,note=n,velocity=vel,time=time));track.append(Message('note_off',channel=ch,note=n,velocity=0,time=dur))
def add_ks(track,a,ch=0):track.append(Message('note_on',channel=ch,note=KS+a,velocity=1,time=0));track.append(Message('note_off',channel=ch,note=KS+a,velocity=0,time=1))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='datasets/symbolic/mandarin_ballad_q4');ap.add_argument('--count',type=int,default=64);ap.add_argument('--seed',type=int,default=260829);a=ap.parse_args();random.seed(a.seed)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);tpb=480
    for k in range(a.count):
        bpm=random.randint(58,82);tonic=random.choice(KEYS);prog=random.choice(PROGS);mid=MidiFile(ticks_per_beat=tpb)
        meta=MidiTrack();mid.tracks.append(meta);meta.append(MetaMessage('set_tempo',tempo=bpm2tempo(bpm),time=0));meta.append(MetaMessage('time_signature',numerator=4,denominator=4,time=0))
        for ch in range(4):
            tr=MidiTrack();mid.tracks.append(tr);add_cc(tr,1,48+random.randint(-5,5),ch=ch);add_cc(tr,3,62+random.randint(-6,6),ch=ch);add_cc(tr,11,112,ch=ch);add_ks(tr,ART['legato' if ch<3 else 'sustain'],ch)
            for bar in range(16):
                root=tonic+prog[bar%4]; tri=[root,root+4,root+7]
                # Ballad-oriented voice leading: lyrical top, close inner voices, cello roots/fifths.
                if ch==0: note=tri[(bar//2)%3]+24+(2 if bar%8==7 else 0)
                elif ch==1: note=tri[(bar+1)%3]+12
                elif ch==2: note=tri[(bar+2)%3]+7
                else: note=root-12+(7 if bar%4==3 else 0)
                swell=int(38+65*(.5-.5*math.cos(math.pi*(bar%8)/7)));add_cc(tr,1,swell,ch=ch);add_cc(tr,3,45+int(.45*swell),ch=ch);add_cc(tr,11,104+int(.15*swell),ch=ch)
                dur=tpb*4
                add_note(tr,max(36,min(96,note)),dur,ch=ch,vel=62+int(.15*swell),time=0)
        mid.save(out/f'ballad_q4_{k:03d}_{bpm}bpm.mid')
    print('generated',a.count,'copyright-clean Q4 MIDI studies in',out)
if __name__=='__main__':main()
