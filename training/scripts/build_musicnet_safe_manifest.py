from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('metadata_csv');ap.add_argument('audio_root');ap.add_argument('--out',default='datasets/manifests/musicnet_strings_safe.jsonl');a=ap.parse_args();rows=[]
    root=Path(a.audio_root);wav_by_stem={p.stem:p for p in root.rglob('*.wav')}
    with open(a.metadata_csv,encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            text=' '.join(str(v) for v in r.values()).lower()
            if not any(k in text for k in ['violin','viola','cello','string quartet','string quintet','piano trio','piano quintet']): continue
            tid=str(r.get('id') or r.get('ID') or r.get('track_id') or '').strip()
            if not tid: continue
            wav=wav_by_stem.get(tid)
            if not wav: continue
            source=str(r.get('source') or r.get('Source') or r.get('recording_source') or '').strip()
            rows.append({'audio':str(wav.resolve()),'dataset':'musicnet_audited','track_id':tid,
                         'license':'CC-BY-4.0 (MusicNet dataset record; retain original track provenance)',
                         'source_url':source or 'https://zenodo.org/records/5120004','source_metadata':r,
                         'release_blocked':False,'role':'realism_critic_only'})
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8');print('MusicNet string/chamber context rows',len(rows),'->',out)
if __name__=='__main__':main()
