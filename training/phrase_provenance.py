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


def _enabled_parent(parent: Mapping | None) -> dict | None:
    if not isinstance(parent,Mapping) or not parent.get('enabled'):
        return None
    pid=str(parent.get('provenance_id','')).lower()
    if len(pid)!=64 or any(c not in '0123456789abcdef' for c in pid):
        raise ValueError('parent phrase provenance has invalid provenance_id')
    return dict(parent)


def build_phrase_provenance(rows: Sequence[Mapping], index_path: str | Path, parent: Mapping | None = None) -> dict:
    parent=_enabled_parent(parent)
    phrase=[r for r in rows if str(r.get('phrase_family') or '').strip()]
    for r in phrase:
        origin=str(r.get('training_origin') or r.get('source_kind') or '').strip().lower()
        if origin not in {'modeled','synthetic','physics','physical','cleanroom'}:
            raise ValueError('phrase-supervised row is not in the MODELED lane')
    enabled=bool(phrase or parent)
    families=sorted({str(r.get('phrase_family')).strip() for r in phrase})
    datasets=sorted({str(r.get('dataset') or r.get('dataset_id') or 'unknown').strip().lower() for r in phrase})
    core={
        'schema':SCHEMA,'version':VERSION,'enabled':enabled,
        'required_release_schema':REQUIRED_RELEASE_SCHEMA if enabled else None,
        'source_index_sha256':file_sha256(index_path),
        'phrase_row_count':len(phrase),'phrase_families':families,'phrase_datasets':datasets,
        'cleanroom_modeled_only':True if phrase else None,
        'inherited_from_parent':bool(parent),
        'parent_provenance_id':parent.get('provenance_id') if parent else None,
    }
    core['provenance_id']=hashlib.sha256(_canonical(core)).hexdigest()
    return core


def requires_schema8(checkpoint: Mapping) -> bool:
    p=checkpoint.get('phrase_finetune_provenance') if isinstance(checkpoint,Mapping) else None
    return bool(isinstance(p,Mapping) and p.get('enabled'))


def validate_checkpoint_phrase_provenance(checkpoint: Mapping) -> dict | None:
    p=checkpoint.get('phrase_finetune_provenance') if isinstance(checkpoint,Mapping) else None
    if not isinstance(p,Mapping) or not p.get('enabled'):
        return None
    if int(p.get('schema',0))!=SCHEMA or p.get('version')!=VERSION or int(p.get('required_release_schema',0))!=REQUIRED_RELEASE_SCHEMA:
        raise ValueError('invalid phrase_finetune_provenance contract')
    pid=str(p.get('provenance_id','')).lower()
    if len(pid)!=64 or any(c not in '0123456789abcdef' for c in pid):
        raise ValueError('invalid phrase_finetune_provenance id')
    return dict(p)
