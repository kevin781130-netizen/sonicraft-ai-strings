from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import numpy as np,soundfile as sf,torch,torchaudio
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from models.string_vae64 import StringVAE64

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refs',required=True);ap.add_argument('--checkpoint',required=True);ap.add_argument('--out-dir',required=True);a=ap.parse_args()
    dev='cuda' if torch.cuda.is_available() else 'cpu';ck=torch.load(a.checkpoint,map_location='cpu',weights_only=False)
    if ck.get('codec_kind')!='strings_vae64' or 'model' not in ck:raise SystemExit('full strings_vae64 checkpoint required (encoder+decoder)')
    m=StringVAE64(**dict(ck.get('config') or {})).to(dev).eval();m.load_state_dict(ck['model'],strict=True);out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    refs=[json.loads(x) for x in Path(a.refs).read_text().splitlines() if x.strip()]
    for r in refs:
        x,sr=sf.read(r['reference'],dtype='float32',always_2d=True);w=torch.from_numpy(np.asarray(x).T).mean(0,keepdim=True)
        if sr!=m.sample_rate:w=torchaudio.functional.resample(w,sr,m.sample_rate)
        n=w.shape[-1]
        # pad to codec stride then trim, avoiding edge-length ambiguity.
        pad=(-n)%m.downsampling_ratio
        if pad:w=torch.nn.functional.pad(w,(0,pad))
        with torch.inference_mode():z=m.encode(w[None].to(dev),sample=False);y=m.decode(z)[0,0].float().cpu()[:n]
        sf.write(out/r['filename'],y.numpy(),m.sample_rate,subtype='FLOAT')
    print('reconstructed',len(refs),'clips ->',out)
if __name__=='__main__':main()
