from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import numpy as np, torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.string_codec import StringCodec
from models.string_vae64 import StringVAE64


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--codec',default='checkpoints/strings_vae64.pt'); ap.add_argument('--index',default='datasets/processed/urmp48/index.jsonl'); a=ap.parse_args()
    dev='cuda' if torch.cuda.is_available() else 'cpu'; ck=torch.load(a.codec,map_location='cpu'); kind=str(ck.get('codec_kind','legacy_stringcodec'))
    if kind=='strings_vae64':
        cfg=dict(ck.get('config') or {}); m=StringVAE64(**cfg).to(dev); m.load_state_dict(ck['model'],strict=True)
        latent_hz=float(ck.get('latent_hz',m.latent_hz)); sample_rate=int(ck.get('codec_sample_rate',m.sample_rate)); latent_ch=int(ck.get('latent_ch',m.latent_dim))
        enc=lambda x:m.encode(x,sample=False)
    else:
        m=StringCodec(ck.get('latent',96)).to(dev); m.load_state_dict(ck['model']); latent_ch=int(ck.get('latent',96)); latent_hz=float(ck.get('latent_hz',187.5)); sample_rate=int(ck.get('codec_sample_rate',48000)); enc=m.encode
    m.eval(); rows=[json.loads(x) for x in Path(a.index).read_text().splitlines() if x.strip()]
    with torch.inference_mode():
        for r in rows:
            p=Path(r['file']); raw=np.load(p,allow_pickle=False); payload={k:raw[k] for k in raw.files}
            x=torch.from_numpy(payload['audio'].astype('float32'))[None,None].to(dev); z=enc(x).cpu().numpy().astype('float16')
            payload.update(latent=z[0],codec_kind=np.array(kind),latent_ch=np.int32(latent_ch),latent_hz=np.float32(latent_hz),codec_sample_rate=np.int32(sample_rate))
            np.savez_compressed(p,**payload)
    print('encoded',len(rows),'codec',kind,'latent',latent_ch,'@',latent_hz,'Hz')
if __name__=='__main__':main()
