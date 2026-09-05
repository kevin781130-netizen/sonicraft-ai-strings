from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vibrato_control import depth_cents_to_cc3, default_vibrato_rate_hz, default_vibrato_jitter
from tempo_conditioning import tempo_features, speed_profile_norm

ART={'arco':0,'sustain':0,'legato':1,'portamento':2,'expressive long':3,'expressive':3,'marcato':4,'staccato':5,'spiccato':6,'tremolo':7,'pizzicato':8,'pizz':8,'trill':9,'harmonic':10,'flautando':11}
DYN={'ppp':.10,'pp':.18,'p':.30,'mp':.42,'mf':.58,'f':.74,'ff':.90,'fff':.97}
INS={'violin':0,'viola':1,'violoncello':2,'cello':2}
NOTE_RE=re.compile(r'(?<![A-Za-z])([A-Ga-g])([#b]?)(-?\d)(?!\d)')

def midi_note(text):
    matches=list(NOTE_RE.finditer(text))
    if not matches:return None
    m=matches[-1];name=m.group(1).upper()+m.group(2);octv=int(m.group(3))
    pc={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}[name]
    return 12*(octv+1)+pc

def norm01(v,default=.5):
    if v is None:return float(default),0.0
    try:
        x=float(v)
        if x>1.0:x/=127.0
        return max(0.,min(1.,x)),1.0
    except Exception:return float(default),0.0

def dynamic_value(row):
    raw=row.get('dynamic',row.get('dynamics'))
    if raw is None:return .58,0.0
    key=str(raw).strip().lower()
    if key in DYN:return DYN[key],1.0
    return norm01(raw,.58)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',action='append',required=True);ap.add_argument('--out',default='datasets/processed/ballad_isolated/index.jsonl');a=ap.parse_args()
    rows=[]
    for mf in a.manifest:
        for line in Path(mf).read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            r=json.loads(line)
            if r.get('release_blocked'):raise RuntimeError(f'Blocked source in commercial renderer input: {r.get("audio") or r.get("path") or r.get("file")}')
            audio=r.get('audio') or r.get('path') or r.get('file')
            if not audio:continue
            fn=Path(audio).name; pitch=r.get('midi_note') if r.get('midi_note') is not None else midi_note(fn)
            try:pitch=int(round(float(pitch)))
            except Exception:continue
            inst=INS.get(str(r.get('instrument','')).lower())
            if inst is None:continue
            if 'scale' in str(r.get('klass','')).lower():continue
            art_raw=str(r.get('articulation','arco')).lower();art=ART.get(art_raw,0);dyn,dyn_known=dynamic_value(r)

            depth=r.get('vibrato_depth_cents')
            if depth is not None:
                try: vib=float(depth_cents_to_cc3(float(depth)));vib_known=float(r.get('vibrato_known',1.0))
                except Exception: vib,vib_known=.0,.0
            else:
                vib,vib_known=norm01(r.get('vibrato',r.get('cc3')),.0)
            exp,exp_known=norm01(r.get('expression',r.get('cc11')),.90);pb,pb_known=norm01(r.get('pitchbend'),.50)
            leg=0.0;leg_known=1.0
            bpm=float(r.get('tempo_bpm',68.0));dur_b=float(r.get('note_duration_beats',2.0));speed=r.get('speed_profile','auto')
            timing_known=float(r.get('timing_known',1.0 if 'tempo_bpm' in r else 0.0))
            tf=tempo_features(bpm,dur_b,art,float(r.get('transition_speed',.5)),speed)
            vib_rate=float(r.get('vibrato_rate_hz',default_vibrato_rate_hz(vib,pitch,inst,bpm,speed)))
            vib_jit=float(r.get('vibrato_jitter',default_vibrato_jitter(vib)))
            rows.append({
                'audio':audio,'dataset':r.get('dataset') or r.get('dataset_id') or 'unknown','instrument':inst,'pitch':pitch,'articulation':art,
                'dynamics':dyn,'vibrato':vib,'expression':exp,'velocity':dyn,'legato':leg,'pitchbend':pb,
                'vibrato_depth_cents':float(depth or 0.0),'vibrato_rate_hz':vib_rate,'vibrato_jitter':vib_jit,
                **tf,'timing_known':timing_known,
                'dynamics_known':dyn_known,'vibrato_known':vib_known,'expression_known':exp_known,'legato_known':leg_known,'pitchbend_known':pb_known,
                'player':0 if inst==0 else (2 if inst==1 else 3),'release_blocked':False
            })
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(json.dumps(x) for x in rows),encoding='utf-8')
    print('isolated control rows',len(rows),out)
    if rows:print('known ratios:',{k:round(sum(float(r[k]) for r in rows)/len(rows),3) for k in ['dynamics_known','vibrato_known','expression_known','legato_known','pitchbend_known','timing_known']})
if __name__=='__main__':main()
