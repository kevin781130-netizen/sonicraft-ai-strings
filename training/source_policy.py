from __future__ import annotations
import json
from pathlib import Path

class SourcePolicyError(RuntimeError): pass

def load_registry(path: str|Path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def dataset_id(row):
    return str(row.get('dataset') or row.get('dataset_id') or 'unknown')

def assert_commercial_sources(dataset_ids, registry_path='training/dataset_registry.json'):
    reg=load_registry(registry_path)
    errors=[]
    for sid in sorted(set(str(x) for x in dataset_ids)):
        item=reg.get(sid)
        if not item:
            errors.append(f'{sid}: unknown source id')
            continue
        if item.get('release_blocked', True): errors.append(f'{sid}: release_blocked=true')
        if not item.get('commercial_safe', False): errors.append(f'{sid}: commercial_safe=false')
    if errors:
        raise SourcePolicyError('Commercial source gate failed:\n  - '+'\n  - '.join(errors))
    return True

def validate_index(index_path, registry_path='training/dataset_registry.json'):
    rows=[]
    for line in Path(index_path).read_text(encoding='utf-8').splitlines():
        if line.strip(): rows.append(json.loads(line))
    for r in rows:
        if r.get('release_blocked'): raise SourcePolicyError(f"row blocked: {r.get('file') or r.get('audio') or r.get('path')}")
    assert_commercial_sources([dataset_id(r) for r in rows], registry_path)
    return len(rows)
