from __future__ import annotations
import argparse, csv, hashlib, json, random, shutil
from pathlib import Path

AUDIO_EXT={'.wav','.flac','.aif','.aiff'}

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

def files_by_stem(d:Path):
    return {p.stem:p for p in d.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXT}

def main():
    ap=argparse.ArgumentParser(description='Prepare a double-blind real-vs-generated pair test. The public folder contains no answer labels.')
    ap.add_argument('--real-dir',required=True); ap.add_argument('--generated-dir',required=True); ap.add_argument('--out',required=True)
    ap.add_argument('--seed',type=int,default=260830); ap.add_argument('--min-trials',type=int,default=20)
    a=ap.parse_args(); real=files_by_stem(Path(a.real_dir)); gen=files_by_stem(Path(a.generated_dir)); stems=sorted(real.keys()&gen.keys())
    if len(stems)<a.min_trials: raise SystemExit(f'need >= {a.min_trials} matched held-out pairs; found {len(stems)}')
    out=Path(a.out); pub=out/'public'; prv=out/'private';
    if out.exists(): shutil.rmtree(out)
    pub.mkdir(parents=True); prv.mkdir(parents=True)
    rng=random.Random(a.seed); key=[]; rows=[]
    for i,stem in enumerate(stems,1):
        tid=f'T{i:03d}'; generated_side=rng.choice(['A','B'])
        pa=gen[stem] if generated_side=='A' else real[stem]; pb=real[stem] if generated_side=='A' else gen[stem]
        ea=pa.suffix.lower(); eb=pb.suffix.lower()
        namea=f'{tid}_A{ea}'; nameb=f'{tid}_B{eb}'
        shutil.copy2(pa,pub/namea); shutil.copy2(pb,pub/nameb)
        rows.append({'trial_id':tid,'A_file':namea,'B_file':nameb,'pick_generated':'','confidence_1_5':'','notes':''})
        key.append({'trial_id':tid,'source_stem':stem,'generated_side':generated_side,
                    'A_sha256':sha256(pub/namea),'B_sha256':sha256(pub/nameb)})
    with (pub/'responses.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    (pub/'README.txt').write_text('Blind test: for every trial, listen to A and B and enter A or B under pick_generated. Do not inspect the private folder until all responses are locked. Use only held-out real recordings and generated renders never used for training.\n',encoding='utf-8')
    (prv/'answer_key.json').write_text(json.dumps({'schema':1,'seed':a.seed,'trials':key},indent=2),encoding='utf-8')
    print(f'Prepared {len(rows)} blind trials at {out}')
    print('IMPORTANT: keep private/answer_key.json away from listeners until responses are final.')
if __name__=='__main__': main()
