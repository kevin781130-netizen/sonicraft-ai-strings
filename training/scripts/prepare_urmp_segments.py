from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np, soundfile as sf
import torch, torchaudio
from tqdm import tqdm

INS={'violin':0,'viola':1,'cello':2}

def hz_to_midi(h): return 69.0+12.0*math.log2(max(h,1e-9)/440.0)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',default='datasets/manifests/urmp_strings.jsonl'); ap.add_argument('--out',default='datasets/processed/urmp48'); ap.add_argument('--seconds',type=float,default=4.0); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True); rows=[]
    src=[json.loads(x) for x in Path(a.manifest).read_text(encoding='utf-8').splitlines() if x.strip()]
    target_sr=48000; fps=25; seg_n=int(a.seconds*target_sr); frames=int(a.seconds*fps)
    for ri,row in enumerate(tqdm(src)):
        wav,sr=sf.read(row['audio'],always_2d=True); wav=wav.mean(1).astype('float32')
        t=torch.from_numpy(wav)[None]
        if sr!=target_sr:t=torchaudio.functional.resample(t,sr,target_sr)
        wav=t[0].numpy(); notes=np.loadtxt(row['notes']); notes=np.atleast_2d(notes)
        duration=len(wav)/target_sr
        for si,start in enumerate(np.arange(0,max(0,duration-a.seconds+1e-6),a.seconds)):
            st=int(start*target_sr); clip=wav[st:st+seg_n]
            if len(clip)<seg_n:continue
            pitch=np.zeros(frames,np.float32); gate=np.zeros(frames,np.float32)
            for onset,hz,dur in notes:
                on=max(onset,start); off=min(onset+dur,start+a.seconds)
                if off<=on:continue
                f0=max(0,min(frames-1,int((on-start)*fps))); f1=max(f0+1,min(frames,int(math.ceil((off-start)*fps))))
                pitch[f0:f1]=hz_to_midi(float(hz)); gate[f0:f1]=1.
            # weak dynamics target from local RMS; later replaced by true CC/semantic data
            x=torch.from_numpy(clip); hop=target_sr//fps; dyn=[]
            for fi in range(frames): dyn.append(float(x[fi*hop:(fi+1)*hop].pow(2).mean().sqrt().clamp(0,1)))
            dyn=np.array(dyn,np.float32); dyn=dyn/(dyn.max()+1e-6)
            fn=out/f'{ri:04d}_{si:04d}.npz'; np.savez_compressed(fn,audio=clip,pitch=pitch,gate=gate,dynamics=dyn,instrument=np.int64(INS[row['instrument']]))
            rows.append({'file':str(fn.resolve()),'source':row['audio'],'release_blocked':row.get('release_blocked',True)})
    idx=out/'index.jsonl'; idx.write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8'); print('segments',len(rows),idx)
if __name__=='__main__':main()
