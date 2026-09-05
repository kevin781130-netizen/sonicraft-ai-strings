from __future__ import annotations
import argparse, json, re
from pathlib import Path
import soundfile as sf

ALIASES={'violin':'violin','viola':'viola','cello':'cello','violoncello':'cello'}

def infer_artic(path: Path):
    s=str(path).lower()
    if 'pizz' in s: return 'pizzicato'
    return 'arco'

def infer_dyn(path: Path):
    s=path.name.lower()
    # Iowa filenames commonly carry dynamic text; unknown stays explicit rather than guessed.
    for d in ('pp','mf','ff','p','f'):
        if re.search(rf'(^|[._ -]){d}([._ -]|$)',s): return d
    return 'unknown'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='datasets/raw/IowaMIS'); ap.add_argument('--out',default='datasets/manifests/iowa_strings.jsonl'); a=ap.parse_args()
    root=Path(a.root); rows=[]
    for p in root.rglob('*'):
        if p.suffix.lower() not in {'.wav','.aif','.aiff','.flac'}: continue
        text=str(p).lower(); inst=next((v for k,v in ALIASES.items() if k in text),None)
        if inst not in {'violin','viola','cello'}: continue
        try: info=sf.info(str(p))
        except Exception as e:
            print('skip unreadable',p,e); continue
        rows.append({
            'audio': str(p.resolve()), 'dataset':'iowa_mis', 'instrument':inst,
            'articulation':infer_artic(p), 'dynamic':infer_dyn(p),
            'sample_rate':info.samplerate, 'channels':info.channels,
            'license':'USE_ANY_PROJECT_NO_RESTRICTIONS_PER_SOURCE_SITE',
            'source':'https://theremin.music.uiowa.edu/MIS.html',
            'release_blocked':False
        })
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+('\n' if rows else ''),encoding='utf-8')
    print('wrote',len(rows),'rows to',out)
    if not rows: raise SystemExit('No Iowa string files found; run fetch_iowa_strings.py first.')
if __name__=='__main__': main()
