from __future__ import annotations
"""Independent training-provenance attestation for phrase-supervised releases.

This record lives in training_provenance.json and is intentionally separate from
checkpoint metadata. Release Schema 8 can therefore require agreement between the
training-data record and each renderer checkpoint lineage.
"""
from typing import Mapping
import hashlib, json

SCHEMA = 1
VERSION = 'phrase_training_provenance_v1'
REQUIRED_RELEASE_SCHEMA = 8


def _sha256_like(value) -> bool:
    s = str(value or '').lower()
    return len(s) == 64 and all(c in '0123456789abcdef' for c in s)


def _canonical(value: Mapping) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _digest_core(value: Mapping) -> str:
    core = {k: v for k, v in value.items() if k != 'attestation_id'}
    return hashlib.sha256(_canonical(core)).hexdigest()


def build_phrase_training_attestation(output_index_sha256: str, curriculum_report_sha256: str) -> dict:
    index_sha = str(output_index_sha256 or '').lower()
    report_sha = str(curriculum_report_sha256 or '').lower()
    if not _sha256_like(index_sha):
        raise ValueError('invalid phrase output index SHA-256')
    if not _sha256_like(report_sha):
        raise ValueError('invalid phrase curriculum report SHA-256')
    core = {
        'schema': SCHEMA,
        'version': VERSION,
        'enabled': True,
        'required_release_schema': REQUIRED_RELEASE_SCHEMA,
        'source_index_sha256': index_sha,
        'curriculum_report_sha256': report_sha,
        'modeled_lane_only': True,
    }
    core['attestation_id'] = _digest_core(core)
    return core


def validate_phrase_training_attestation(value: Mapping | None) -> dict | None:
    if not isinstance(value, Mapping) or not value.get('enabled'):
        return None
    att = dict(value)
    if int(att.get('schema', 0)) != SCHEMA or att.get('version') != VERSION:
        raise ValueError('invalid phrase training provenance contract')
    if int(att.get('required_release_schema', 0)) != REQUIRED_RELEASE_SCHEMA:
        raise ValueError('invalid phrase training release schema floor')
    if att.get('modeled_lane_only') is not True:
        raise ValueError('phrase training provenance must remain MODELED-only')
    if not _sha256_like(att.get('source_index_sha256')):
        raise ValueError('invalid phrase training source index SHA-256')
    if not _sha256_like(att.get('curriculum_report_sha256')):
        raise ValueError('invalid phrase curriculum report SHA-256')
    aid = str(att.get('attestation_id', '')).lower()
    if not _sha256_like(aid) or _digest_core(att) != aid:
        raise ValueError('invalid phrase training attestation id')
    return att
