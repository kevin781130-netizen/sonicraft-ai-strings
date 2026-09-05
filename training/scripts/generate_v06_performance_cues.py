from __future__ import annotations
import argparse,csv,sys
from pathlib import Path
from mido import MidiFile,MidiTrack,Message,MetaMessage,bpm2tempo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vibrato_control import CC3_ANCHORS,DEPTH_CENTS_ANCHORS,DEPTH_NAMES
from tempo_conditioning import SPEED_PROFILE_CC20,transition_target_ms
TPB=480;KS=24
PARTS={'VlnI':('Violin I',[60,67,72]),'VlnII':('Violin II',[59,64,71]),'Viola':('Viola',[52,60,67]),'Cello':('Cello',[40,48,55])}
ART={'sustain':0,'legato':1,'portamento':2,'expressive':3}

def save(path,bpm,events,name):
    tr=MidiTrack();tr.append(MetaMessage('track_name',name=name,time=0));tr.append(MetaMessage('set_tempo',tempo=bpm2tempo(bpm),time=0));last=0
    for tick,order,msg in sorted(events,key=lambda x:(x[0],x[1])):msg.time=max(0,int(tick-last));tr.append(msg);last=tick
    m=MidiFile(ticks_per_beat=TPB);m.tracks.append(tr);path.parent.mkdir(parents=True,exist_ok=True);m.save(path)
def cc(ev,t,c,v):ev.append((t,1,Message('control_change',control=c,value=max(0,min(127,int(v))),time=0)))
def note(ev,s,e,n,v=70):ev.extend([(s,5,Message('note_on',note=n,velocity=v,time=0)),(e,0,Message('note_off',note=n,velocity=0,time=0))])
def ks(ev,t,a):n=KS+ART[a];ev.extend([(t,1,Message('note_on',note=n,velocity=1,time=0)),(t+24,0,Message('note_off',note=n,velocity=0,time=0))])
def marker(ev,t,text):ev.append((t,2,MetaMessage('marker',text=text,time=0)))

def vibrato_grid(part,name,notes,out,rows):
    for bpm in (58,68,82):
        ev=[];tick=0;ks(ev,0,'expressive')
        for n in notes:
            for prof in ('slow','normal','fast'):
                cc20=SPEED_PROFILE_CC20[prof];cc(ev,tick,20,cc20)
                for cc3v,depth,label in zip(CC3_ANCHORS,DEPTH_CENTS_ANCHORS,DEPTH_NAMES):
                    marker(ev,tick,f'{name} VIBRATO {label} {prof} CC3={cc3v} target={depth:.0f}c BPM={bpm}');cc(ev,tick,1,66);cc(ev,tick,11,112);cc(ev,tick,3,0)
                    if cc3v>0:cc(ev,tick+TPB//2,3,cc3v)
                    note(ev,tick,tick+TPB*4,n,70);rows.append([part,'vibrato_depth_rate',bpm,'expressive',prof,n,n,0,cc3v,depth,'4 beats; CC3 controls depth; speed profile requests slow/normal/fast human vibrato rate without metronome phase-lock'])
                    tick+=TPB*5
        save(out/f'{part}_04_vibrato_depth_{bpm}bpm.mid',bpm,ev,f'{name} Vibrato Depth {bpm}')

def transition_grid(part,name,notes,out,rows):
    intervals=(2,5,7)
    for bpm in (56,68,84):
        ev=[];tick=0
        for art in ('legato','portamento'):
            ks(ev,tick,art)
            for prof in ('slow','normal','fast'):
                cc20=SPEED_PROFILE_CC20[prof];cc(ev,tick,20,cc20)
                for n in notes[:2]:
                    for iv in intervals:
                        target=n+iv;ms=transition_target_ms(bpm,art,.5,prof);overlap_beats=ms/(60000.0/bpm);overlap=max(12,int(overlap_beats*TPB))
                        marker(ev,tick,f'{name} {art.upper()} {prof} {iv:+d}st {ms:.0f}ms BPM={bpm}');cc(ev,tick,1,66);cc(ev,tick,3,64);cc(ev,tick,11,112)
                        note(ev,tick,tick+TPB*2,n);note(ev,tick+TPB*2-overlap,tick+TPB*4-overlap,target)
                        rows.append([part,'transition',bpm,art,prof,n,target,iv,64,28.0,f'target transition ~{ms:.0f}ms; natural connection'])
                        tick+=TPB*5
        save(out/f'{part}_05_transition_speed_{bpm}bpm.mid',bpm,ev,f'{name} Transition Speed {bpm}')

def bow_grid(part,name,notes,out,rows):
    for bpm in (56,68,84):
        ev=[];tick=0;ks(ev,0,'legato')
        for prof in ('slow','normal','fast'):
            cc20=SPEED_PROFILE_CC20[prof];cc(ev,tick,20,cc20)
            for n in notes:
                marker(ev,tick,f'{name} BOW-CHANGE {prof} BPM={bpm}');cc(ev,tick,1,60);cc(ev,tick,3,58);cc(ev,tick,11,112)
                # Four same-pitch notes with tiny overlaps: performer should re-bow without accenting every change.
                t=tick
                for _ in range(4):note(ev,t,t+TPB+20,n,66);t+=TPB
                rows.append([part,'bow_change',bpm,'legato',prof,n,n,0,58,25.0,'four controlled re-bows; minimize artificial accent, retain bow texture'])
                tick+=TPB*5
        save(out/f'{part}_06_bow_change_{bpm}bpm.mid',bpm,ev,f'{name} Bow Change {bpm}')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='datasets/recording_cues/mandarin_ballad_q4_v06');a=ap.parse_args();out=Path(a.out);rows=[]
    for part,(name,notes) in PARTS.items():vibrato_grid(part,name,notes,out,rows);transition_grid(part,name,notes,out,rows);bow_grid(part,name,notes,out,rows)
    with (out/'session_plan_v06.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['part','exercise','bpm','articulation','speed_profile','source_note','target_note','interval_semitones','cc3','target_vibrato_depth_cents','instruction']);w.writerows(rows)
    (out/'README.txt').write_text('v0.6 focused recording cues: 5 CC3 anchors (straight + four active depths), 3 transition speeds, 3 song tempos, and bow-change grids.\nCC20 is optional Cubase Expression-Map speed profile: Auto=0 Slow=42 Normal=84 Fast=127.\nRecord 24-bit/96-kHz dry/close masters and retain per-player/take IDs plus signed commercial ML/model-weight rights.\n',encoding='utf-8')
    print('generated',len(rows),'v0.6 performance rows in',out)
if __name__=='__main__':main()
