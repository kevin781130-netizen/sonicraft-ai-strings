#!/usr/bin/env python3
"""Optional MIT TorchFCPE challenger for offline real-string F0 extraction.

FCPE is never required by the VST/runtime. Use it beside torchcrepe and promote it only
on measured pitch/transition accuracy and analysis throughput.
"""
import argparse, json
from pathlib import Path
import torch, torchaudio
try:
    import torchfcpe
except ImportError as e:
    raise SystemExit("Install/fetch TorchFCPE first: scripts\\FETCH_MIT_ACCELERATORS.bat") from e

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('audio'); ap.add_argument('--out',required=True)
    ap.add_argument('--hop',type=int,default=160); ap.add_argument('--fmin',type=float,default=40.0); ap.add_argument('--fmax',type=float,default=1800.0)
    a=ap.parse_args(); wav,sr=torchaudio.load(a.audio); wav=wav.mean(0,keepdim=True)
    target_sr=16000
    if sr!=target_sr: wav=torchaudio.functional.resample(wav,sr,target_sr); sr=target_sr
    dev='cuda' if torch.cuda.is_available() else 'cpu'; model=torchfcpe.spawn_bundled_infer_model(device=dev)
    audio=wav[0].to(dev).float().unsqueeze(0).unsqueeze(-1)
    n=(audio.shape[1]//a.hop)+1
    with torch.inference_mode():
        f0=model.infer(audio,sr=sr,decoder_mode='local_argmax',threshold=.006,f0_min=a.fmin,f0_max=a.fmax,
                       interp_uv=False,output_interp_target_length=n)
    f0=f0.reshape(-1).detach().cpu(); rows=[]
    for i,v in enumerate(f0):
        hz=float(v); rows.append({'time_s':i*a.hop/sr,'f0_hz':hz if hz>0 else 0.0,'voiced':bool(hz>0)})
    Path(a.out).write_text(json.dumps({'audio':str(Path(a.audio).resolve()),'tracker':'torchfcpe','sr_analysis':sr,'hop':a.hop,'frames':rows}),encoding='utf-8')
    print(f'wrote {len(rows)} FCPE frames -> {a.out}')
if __name__=='__main__': main()
