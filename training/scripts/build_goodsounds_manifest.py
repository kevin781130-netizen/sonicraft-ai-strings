from __future__ import annotations
import argparse, json, pathlib, hashlib

def load_json(root,name):
    matches=list(root.rglob(name))
    if not matches: raise FileNotFoundError(name)
    return json.load(open(matches[0],encoding='utf-8'))

def to_map(v):
    if isinstance(v,dict): return {str(k):x for k,x in v.items()}
    if isinstance(v,list): return {str(x.get('id',i)):x for i,x in enumerate(v)}
    raise TypeError(type(v))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--out',default='good_sounds_strings_manifest.jsonl')
    args=ap.parse_args(); root=pathlib.Path(args.root)
    sounds=to_map(load_json(root,'sounds.json')); takes=to_map(load_json(root,'takes.json'))
    files={p.name:p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in {'.wav','.flac','.aif','.aiff'}}
    keep=[]
    for tid,t in takes.items():
        sid=str(t.get('sound_id')); s=sounds.get(sid)
        if not s: continue
        inst=str(s.get('instrument','')).lower(); klass=str(s.get('klass','')).lower()
        if inst not in {'violin','cello'}: continue
        if not ('good-sound' in klass or 'scale-good' in klass): continue
        fn=pathlib.Path(str(t.get('filename',''))).name; p=files.get(fn)
        if not p: continue
        rec={
            'dataset':'good_sounds_cora_2025','audio':str(p.resolve()),'instrument':inst,'klass':klass,
            'midi_note':s.get('semitone'),'dynamic':s.get('dynamics'),'bow_velocity':s.get('bow_velocity'),
            'bridge_position':s.get('bridge_position'),'string':s.get('string'),'microphone':t.get('microphone'),
            'player':s.get('player'),'license':'CC-BY-4.0','release_blocked':False,
            'source_doi':'10.34810/DATA2314'
        }
        keep.append(rec)
    with open(args.out,'w',encoding='utf-8') as f:
        for r in keep: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print('kept',len(keep),'violin/cello good-sound or scale-good takes ->',args.out)
if __name__=='__main__': main()
