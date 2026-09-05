#!/usr/bin/env python3
"""Optional MIT torchcrepe high-resolution analysis path for real string supervision."""
import argparse, json
from pathlib import Path
import torch, torchaudio
try:
    import torchcrepe
except ImportError as e:
    raise SystemExit("Install/fetch torchcrepe first: scripts\\FETCH_MIT_ACCELERATORS.bat") from e

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("audio"); ap.add_argument("--out",required=True); ap.add_argument("--hop",type=int,default=128)
    a=ap.parse_args(); wav,sr=torchaudio.load(a.audio); wav=wav.mean(0,keepdim=True)
    if sr!=16000: wav=torchaudio.functional.resample(wav,sr,16000); sr=16000
    device="cuda" if torch.cuda.is_available() else "cpu"; wav=wav.to(device)
    f0,period=torchcrepe.predict(wav,sr,a.hop,40,1800,"full",batch_size=1024,device=device,return_periodicity=True,pad=True)
    f0=f0[0].detach().cpu(); period=period[0].detach().cpu()
    # Confidence-gated pitch curve; later physics extraction computes vibrato/portamento from this.
    keep=period>=0.45
    rows=[{"time_s":i*a.hop/sr,"f0_hz":float(f0[i]) if keep[i] else 0.0,"periodicity":float(period[i])} for i in range(len(f0))]
    Path(a.out).write_text(json.dumps({"audio":str(Path(a.audio).resolve()),"sr_analysis":sr,"hop":a.hop,"frames":rows}),encoding="utf-8")
    print(f"wrote {len(rows)} frames -> {a.out}")
if __name__=="__main__": main()
