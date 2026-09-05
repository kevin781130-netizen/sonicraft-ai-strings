from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np, soundfile as sf
import torch, torchaudio
from vibrato_control import depth_cents_to_cc3


def licensed(dataset,registry):
    reg=json.loads(Path(registry).read_text(encoding='utf-8'));e=reg.get(str(dataset).lower())
    return bool(e and e.get('commercial_safe') and not e.get('release_blocked'))

def estimate(audio_path):
    wav,sr=sf.read(audio_path,dtype='float32',always_2d=True);x=torch.from_numpy(wav.T).mean(0,keepdim=True)
    if sr!=16000:x=torchaudio.functional.resample(x,sr,16000);sr=16000
    if x.shape[-1] < sr//2:return None
    # Torchaudio autocorrelation pitch tracker: deterministic and trained on no external dataset.
    f0=torchaudio.functional.detect_pitch_frequency(x,sr,frame_time=.01,win_length=25,freq_low=55,freq_high=1800)[0].cpu().numpy()
    if len(f0)<30:return None
    lo=max(2,int(.10*len(f0)));hi=max(lo+10,int(.90*len(f0)));f0=f0[lo:hi]
    valid=np.isfinite(f0)&(f0>40)
    if valid.mean()<.65:return None
    f=f0[valid];med=np.median(f)
    cents=1200*np.log2(np.maximum(f,1e-5)/med)
    # Remove slow intonation drift. Vibrato lives mostly around 3.5-8.5 Hz.
    win=max(5,int(.35/.01));kernel=np.ones(win,dtype=np.float32)/win
    trend=np.convolve(cents,kernel,mode='same');res=cents-trend
    depth=.5*(np.percentile(res,95)-np.percentile(res,5))
    y=res-res.mean();freq=np.fft.rfftfreq(len(y),d=.01);power=np.abs(np.fft.rfft(y))**2
    band=(freq>=3.5)&(freq<=8.5)
    if not band.any() or power[band].sum()<=1e-8:return None
    idx=np.where(band)[0][int(np.argmax(power[band]))];rate=float(freq[idx]);periodicity=float(power[idx]/(power[band].sum()+1e-9))
    jitter=float(np.clip(np.std(np.diff(res))/max(4.0,depth),0,0.12))
    confidence=float(np.clip((valid.mean()-.5)*1.8 + periodicity*.8,0,1))
    is_vib=bool(depth>=5.0 and 3.7<=rate<=8.0 and periodicity>=.16 and confidence>=.50)
    return {'vibrato_depth_cents':float(np.clip(depth,0,90)),'vibrato_rate_hz':rate,
            'vibrato_jitter':jitter,'vibrato_confidence':confidence,'vibrato_detected':is_vib,
            'vibrato':float(depth_cents_to_cc3(depth) if is_vib else 0.0),'vibrato_known':1.0}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--registry',default='training/dataset_registry.json');a=ap.parse_args();out=[]
    for line in Path(a.manifest).read_text(encoding='utf-8').splitlines():
        if not line.strip():continue
        r=json.loads(line);src=r.get('dataset') or r.get('dataset_id')
        if not licensed(src,a.registry):raise RuntimeError(f'Refusing vibrato analysis for non-release-cleared dataset: {src}')
        audio=r.get('audio') or r.get('path') or r.get('file')
        if not audio or not Path(audio).exists():continue
        est=estimate(audio)
        if est:r.update(est)
        else:r.update({'vibrato_known':0.0})
        out.append(r)
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(json.dumps(x) for x in out),encoding='utf-8')
    good=sum(1 for x in out if x.get('vibrato_known'));print('analyzed',len(out),'commercial-safe rows; vibrato-supervised',good,'->',p)
if __name__=='__main__':main()
