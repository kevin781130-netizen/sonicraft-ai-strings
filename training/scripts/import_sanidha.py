from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root');ap.add_argument('--out',default='datasets/manifests/sanidha_violin.jsonl');a=ap.parse_args()
    root=Path(a.root); rows=[]
    for p in sorted(root.rglob('violin-*.wav')):
        s=str(p).lower()
        if 'audio-multitracks-clean' not in s: continue
        rows.append({'audio':str(p.resolve()),'dataset':'sanidha','instrument':'violin','license':'CC-BY-4.0','style_policy':'acoustic_only_no_pitch_ornament_supervision','release_blocked':False})
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8');print('rows',len(rows),out)
if __name__=='__main__':main()
