from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def iter_rows(path: Path):
    if path.suffix.lower()=='.jsonl':
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip(): yield json.loads(line)
    else:
        obj=json.loads(path.read_text(encoding='utf-8'))
        if isinstance(obj,list): yield from obj
        elif isinstance(obj,dict) and isinstance(obj.get('items'),list): yield from obj['items']
        else: yield obj

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--registry',default='training/dataset_registry.json')
    ap.add_argument('--manifest',action='append',default=[])
    ap.add_argument('--dataset',action='append',default=[])
    ap.add_argument('--out',default='checkpoints/training_provenance.json')
    a=ap.parse_args()
    reg=json.loads(Path(a.registry).read_text(encoding='utf-8'))
    used=set(a.dataset); items=[]; errors=[]
    for m in a.manifest:
        mp=Path(m)
        if not mp.exists(): errors.append(f'missing manifest: {m}'); continue
        for row in iter_rows(mp):
            ds=row.get('dataset') or row.get('dataset_id')
            if ds: used.add(ds)
            if row.get('release_blocked') is True: errors.append(f'item explicitly release_blocked in {m}: {row.get("file","?")}')
            fp=row.get('file') or row.get('audio') or row.get('path')
            items.append({'manifest':m,'dataset':ds,'file':fp})
    for ds in sorted(used):
        info=reg.get(ds)
        if info is None: errors.append(f'unknown dataset id (fail closed): {ds}'); continue
        if info.get('release_blocked',True): errors.append(f'dataset blocked: {ds} — {info.get("license","no license recorded")}')
        if not info.get('commercial_safe',False): errors.append(f'dataset not marked commercial_safe: {ds}')
    if errors:
        print('RELEASE/TRAINING SOURCE GATE: FAIL')
        for e in errors: print(' -',e)
        sys.exit(2)
    prov={
        'checked_utc':datetime.now(timezone.utc).isoformat(),
        'registry_sha256':sha256(Path(a.registry)),
        'datasets':sorted(used),
        'manifests':[],
        'rule':'Fail closed: blocked, unknown, or non-commercial-safe sources cannot enter a release checkpoint.'
    }
    for m in a.manifest:
        mp=Path(m)
        if mp.exists(): prov['manifests'].append({'path':m,'sha256':sha256(mp)})
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(prov,indent=2),encoding='utf-8')
    print('RELEASE/TRAINING SOURCE GATE: PASS')
    print('datasets:',', '.join(sorted(used)) or '(none)')
    print('provenance:',out)
if __name__=='__main__': main()
