from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import numpy as np, soundfile as sf
import torch, torchaudio
from tqdm import tqdm
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tempo_conditioning import tempo_features
from vibrato_control import default_vibrato_onset_ms, default_vibrato_rate_hz, default_vibrato_jitter

def load_dac(bitrate='16kbps'):
    import dac
    try:path=dac.utils.download(model_type='44khz',model_bitrate=bitrate)
    except TypeError:path=dac.utils.download(model_type='44khz')
    return dac.DAC.load(path)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--index',default='datasets/processed/ballad_isolated/index.jsonl');ap.add_argument('--out',default='datasets/processed/ballad_dac')
    ap.add_argument('--seconds',type=float,default=2.0);ap.add_argument('--bitrate',default='16kbps');a=ap.parse_args()
    dev='cuda' if torch.cuda.is_available() else 'cpu'; model=load_dac(a.bitrate).to(dev).eval(); sr0=44100; n=int(a.seconds*sr0); fps=100; frames=int(a.seconds*fps)
    root=Path(a.out);root.mkdir(parents=True,exist_ok=True);outrows=[]
    rows=[json.loads(x) for x in Path(a.index).read_text(encoding='utf-8').splitlines() if x.strip()]
    for i,r in enumerate(tqdm(rows)):
        wav,sr=sf.read(r['audio'],dtype='float32',always_2d=True);w=torch.from_numpy(wav.T).mean(0,keepdim=True)
        if sr!=sr0:w=torchaudio.functional.resample(w,sr,sr0)
        if w.shape[-1]<n:w=torch.nn.functional.pad(w,(0,n-w.shape[-1]))
        elif w.shape[-1]>n:
            hop=max(1,n//8); best=0;be=-1.
            for st in range(0,w.shape[-1]-n+1,hop):
                e=float(w[...,st:st+n].pow(2).mean())
                if e>be:be=e;best=st
            w=w[...,best:best+n]
        peak=float(w.abs().max());
        if peak>1.0:w=w/peak*.995
        x=model.preprocess(w.to(dev),sr0)
        with torch.no_grad():z,_,_,_,_=model.encode(x)
        z=z[0].float().cpu().numpy();gate=np.ones(frames,np.float32);onset=np.zeros(frames,np.float32);onset[:max(1,fps//50)]=1
        def curve(v):return np.full(frames,float(v),np.float32)
        bpm=float(r.get('tempo_bpm',68));dur_b=float(r.get('note_duration_beats',2));tf=tempo_features(bpm,dur_b,int(r['articulation']),float(r.get('transition_speed',.5)),r.get('speed_profile','auto'))
        vib=float(r.get('vibrato',0));inst=int(r['instrument']);pitch=float(r['pitch'])
        vib_depth=float(r.get('vibrato_depth_cents',0));vib_rate=float(r.get('vibrato_rate_hz',default_vibrato_rate_hz(vib,pitch,inst,bpm,r.get('speed_profile','auto'))))
        vib_on_ms=float(r.get('vibrato_onset_ms',default_vibrato_onset_ms(vib,bpm,dur_b)));vib_jit=float(r.get('vibrato_jitter',default_vibrato_jitter(vib)))
        fn=root/f'{i:06d}.npz';np.savez_compressed(fn,latent=z,pitch=curve(pitch),gate=gate,onset=onset,velocity=curve(r['velocity']),dynamics=curve(r['dynamics']),vibrato=curve(vib),expression=curve(r['expression']),legato=curve(r['legato']),pitchbend=curve(r['pitchbend']),transition_speed=curve(r.get('transition_speed',.50)),short_tightness=curve(r.get('short_tightness',.50)),attack_character=curve(r.get('attack_character',.38)),note_progress=np.linspace(0,1,frames,dtype=np.float32),phrase_position=curve(r.get('phrase_position',.50)),prev_interval=curve(r.get('prev_interval',.50)),next_interval=curve(r.get('next_interval',.50)),bow_change_prob=curve(r.get('bow_change_prob',.25)),vibrato_onset=curve(min(1.0,vib_on_ms/1000.0)),tempo_bpm=curve(tf['tempo_bpm']),seconds_per_beat=curve(tf['seconds_per_beat']),note_duration_beats=curve(tf['note_duration_beats']),transition_target_ms=curve(tf['transition_target_ms']),speed_profile=curve(tf['speed_profile']),vibrato_depth_cents=curve(vib_depth),vibrato_rate_hz=curve(vib_rate),vibrato_onset_ms=curve(vib_on_ms),vibrato_jitter=curve(vib_jit),dynamics_known=curve(r.get('dynamics_known',1.0)),vibrato_known=curve(r.get('vibrato_known',0.0)),expression_known=curve(r.get('expression_known',0.0)),legato_known=curve(r.get('legato_known',1.0)),pitchbend_known=curve(r.get('pitchbend_known',0.0)),timing_known=curve(r.get('timing_known',0.0)),articulation_known=curve(r.get('articulation_known',1.0)),instrument=np.int64(inst),articulation=np.int64(r['articulation']),player=np.int64(r['player']))
        outrows.append({'file':str(fn.resolve()),'dataset':r['dataset'],'release_blocked':False})
    idx=root/'index.jsonl';idx.write_text('\n'.join(json.dumps(x) for x in outrows),encoding='utf-8');print('DAC latent segments',len(outrows),idx)
if __name__=='__main__':main()
