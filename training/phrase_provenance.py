from __future__ import annotations
"""Checkpoint provenance for phrase-supervised renderer training.

The marker is derived from the actual latent index, not a user-supplied boolean.
Once phrase supervision enters a renderer lineage, distillation keeps the marker so
a release cannot silently downgrade to a pre-Schema-8 manifest.
"""
from pathlib import Path
from typing import Mapping, Sequence
import hashlib, json

SCHEMA=1
VERSION='phrase_checkpoint_provenance_v1'
REQUIRED_RELEASE_SCHEMA=8


def file_sha256(path: str | Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def _digest_core(value: Mapping) -> str:
    core={k:v for k,v in value.items() if k!='provenance_id'}
    return hashlib.sha256(_canonical(core)).hexdigest()


def _enabled_parent(parent: Mapping | None) -> dict | None:
    if not isinstance(parent,Mapping) or not parent.get('enabled'):
        return None
    p=dict(parent); pid=str(p.get('provenance_id','')).lower()
    if len(pid)!=64 or any(c not in '0123456789abcdef' for c in pid) or _digest_core(p)!=pid:
        raise ValueError('parent phrase provenance has invalid provenance_id')
    return p


def build_phrase_provenance(rows: Sequence[Mapping], index_path: str | Path, parent: Mapping | None = None) -> dict:
    parent=_enabled_parent(parent)
    phrase=[r for r in rows if str(r.get('phrase_family') or '').strip()]
    for r in phrase:
        origin=str(r.get('training_origin') or r.get('source_kind') or '').strip().lower()
        if origin not in {'modeled','synthetic','physics','physical','cleanroom'}:
            raise ValueError('phrase-supervised row is not in the MODELED lane')
    current_sha=file_sha256(index_path); enabled=bool(phrase or parent)
    families={str(r.get('phrase_family')).strip() for r in phrase}
    datasets={str(r.get('dataset') or r.get('dataset_id') or 'unknown').strip().lower() for r in phrase}
    if parent:
        families.update(str(x) for x in parent.get('phrase_families') or [])
        datasets.update(str(x) for x in parent.get('phrase_datasets') or [])
    root_phrase_sha=current_sha if phrase else (parent.get('phrase_source_index_sha256') if parent else None)
    retained_count=len(phrase) if phrase else (int(parent.get('phrase_row_count',0)) if parent else 0)
    core={
        'schema':SCHEMA,'version':VERSION,'enabled':enabled,
        'required_release_schema':REQUIRED_RELEASE_SCHEMA if enabled else None,
        'source_index_sha256':current_sha,
        'phrase_source_index_sha256':root_phrase_sha,
        'phrase_row_count':retained_count,'local_phrase_row_count':len(phrase),
        'phrase_families':sorted(families),'phrase_datasets':sorted(datasets),
        'cleanroom_modeled_only':True if enabled else None,
        'inherited_from_parent':bool(parent),
        'parent_provenance_id':parent.get('provenance_id') if parent else None,
    }
    core['provenance_id']=_digest_core(core)
    return core


def requires_schema8(checkpoint: Mapping) -> bool:
    p=checkpoint.get('phrase_finetune_provenance') if isinstance(checkpoint,Mapping) else None
    return bool(isinstance(p,Mapping) and p.get('enabled'))


def validate_checkpoint_phrase_provenance(checkpoint: Mapping) -> dict | None:
    p=checkpoint.get('phrase_finetune_provenance') if isinstance(checkpoint,Mapping) else None
    if not isinstance(p,Mapping) or not p.get('enabled'):
        return None
    p=dict(p)
    if int(p.get('schema',0))!=SCHEMA or p.get('version')!=VERSION or int(p.get('required_release_schema',0))!=REQUIRED_RELEASE_SCHEMA:
        raise ValueError('invalid phrase_finetune_provenance contract')
    pid=str(p.get('provenance_id','')).lower()
    if len(pid)!=64 or any(c not in '0123456789abcdef' for c in pid) or _digest_core(p)!=pid:
        raise ValueError('invalid phrase_finetune_provenance id')
    root=str(p.get('phrase_source_index_sha256','')).lower()
    if len(root)!=64 or any(c not in '0123456789abcdef' for c in root):
        raise ValueError('invalid phrase source index digest')
    if p.get('cleanroom_modeled_only') is not True:
        raise ValueError('phrase provenance must remain MODELED-only')
    return p
