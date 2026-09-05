from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--refs',required=True);ap.add_argument('--recon-dir',required=True);ap.add_argument('--candidate-id',required=True);ap.add_argument('--kind',required=True)
    ap.add_argument('--latent-ch',type=int);ap.add_argument('--latent-hz',type=float);ap.add_argument('--decoder-bytes',type=int);ap.add_argument('--out',required=True);ap.add_argument('--append',action='store_true');a=ap.parse_args()
    refs=[json.loads(x) for x in Path(a.refs).read_text().splitlines() if x.strip()];rd=Path(a.recon_dir);rows=[]
    for r in refs:
        rec=rd/r['filename']
        if not rec.is_file():raise SystemExit(f'missing reconstruction: {rec}')
        rows.append({'reference':r['reference'],'reconstruction':str(rec.resolve()),'candidate_id':a.candidate_id,'kind':a.kind,'training_origin':'real','dataset':r.get('dataset'),
                     'latent_ch':a.latent_ch,'latent_hz':a.latent_hz,'decoder_bytes':a.decoder_bytes})
    p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);mode='a' if a.append else 'w'
    with p.open(mode,encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r)+'\n')
    print(('appended' if a.append else 'wrote'),len(rows),'pairs for',a.candidate_id,'->',p)
if __name__=='__main__':main()
