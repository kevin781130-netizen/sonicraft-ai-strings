#!/usr/bin/env python3
from __future__ import annotations
"""Read-only pre-seal validation for a production Release Schema 8 run.

This command intentionally does not import torch and never mutates checkpoints. It
catches path/evidence/corpus/checkpoint mismatches before transition sealing begins.
Passing this preflight is not release approval; the sealer, manifest builder,
commercial gate, GPU evaluation, and listener evidence remain authoritative.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phrase_release_provenance import validate_phrase_training_attestation
from release_transition_gate import assert_release_evidence

PRODUCT = 'SONICRAFT AI Strings Q4'
EXPECTED_CURRICULUM = 'lane_locked_acoustic_promotion_v20'


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def fail(message: str) -> None:
    raise SystemExit('SCHEMA 8 PREFLIGHT FAIL: ' + message)


def require_file(value: str | None, label: str) -> Path:
    if not value:
        fail(label + ' path missing')
    path = Path(value)
    if not path.is_file():
        fail(f'{label} file missing: {path}')
    return path


def load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        fail(f'invalid {label} JSON: {e}')
    if not isinstance(value, dict):
        fail(f'{label} must be a JSON object')
    return value


def sha256_like(value) -> bool:
    s = str(value or '').lower()
    return len(s) == 64 and all(c in '0123456789abcdef' for c in s)


def normalized_dataset_ids(provenance: Mapping) -> list[str]:
    raw = provenance.get('datasets') or provenance.get('dataset_ids') or provenance.get('sources') or []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            key = item
        elif isinstance(item, Mapping):
            key = item.get('dataset_id') or item.get('id') or item.get('dataset')
        else:
            key = None
        if key and str(key) not in out:
            out.append(str(key))
    return out


def validate_training_policy(provenance: Mapping) -> dict:
    policy = dict(provenance.get('training_policy') or {})
    required = (
        'real_probability', 'modeled_probability', 'modeled_timbre_anchor',
        'modeled_adversarial_target', 'curriculum', 'cleanroom_modeled_only',
    )
    missing = [k for k in required if k not in policy]
    if missing:
        fail('training provenance missing policy fields: ' + ', '.join(missing))
    try:
        real = float(policy['real_probability'])
        modeled = float(policy['modeled_probability'])
    except Exception:
        fail('invalid training policy probabilities')
    if abs(real - .80) > 1e-6 or abs(modeled - .20) > 1e-6 or abs(real + modeled - 1.0) > 1e-6:
        fail('Schema 8 preflight requires REAL80/MODEL20')
    if policy['modeled_timbre_anchor'] is not False:
        fail('modeled timbre anchor must remain false')
    if policy['modeled_adversarial_target'] is not False:
        fail('modeled adversarial target must remain false')
    if policy['cleanroom_modeled_only'] is not True:
        fail('clean-room material must remain MODELED-only')
    if str(policy['curriculum']) != EXPECTED_CURRICULUM:
        fail(f'expected curriculum {EXPECTED_CURRICULUM!r}, got {policy.get("curriculum")!r}')
    return policy


def validate_registry(provenance: Mapping, registry: Mapping) -> list[str]:
    used = normalized_dataset_ids(provenance)
    if not used:
        fail('training provenance contains no dataset/source IDs')
    blocked = []
    for key in used:
        entry = registry.get(key)
        if not isinstance(entry, Mapping) or entry.get('release_blocked') or not entry.get('commercial_safe'):
            blocked.append(key)
    if blocked:
        fail('blocked/unknown training sources: ' + ', '.join(sorted(blocked)))
    return used


def validate_metrics(report: Mapping) -> None:
    if report.get('product') not in (None, PRODUCT):
        fail('release metrics product mismatch')
    if not report.get('release_pass'):
        fail('release metrics have not passed')
    gates = ('midi_lock_pass', 'vibrato_monotonic_pass', 'tempo_transition_pass', 'dropout_fallback_pass', 'abx_pass')
    failed = [k for k in gates if not report.get(k)]
    if failed:
        fail('release metric gates not passed: ' + ', '.join(failed))
    abx = dict(report.get('abx') or {})
    accuracy = abx.get('generated_identification_accuracy')
    target = float(abx.get('target_max_accuracy', .60))
    if accuracy is None or float(accuracy) > target:
        fail(f'generated-real ABX identification accuracy {accuracy} exceeds target {target}')
    if int(abx.get('listener_count', 0)) < 3 or int(abx.get('trial_count', 0)) < 20:
        fail('release metrics ABX requires >=3 listeners and >=20 trials')


def validate_sound_forge(report: Mapping, policy: Mapping) -> None:
    if int(report.get('schema', 0)) != 1 or report.get('forge_version') != 'sound_forge_v19' or not report.get('release_pass'):
        fail('Sound Forge evidence failed contract')
    if int(report.get('eligible_real_files', 0)) < 1 or int(report.get('eligible_modeled_files', 0)) < 1:
        fail('Sound Forge requires eligible real + modeled material')
    if int(report.get('rights_failures', 0)) or int(report.get('audio_failures', 0)):
        fail('Sound Forge has unresolved rights/audio failures')
    if dict(report.get('training_policy') or {}) != dict(policy):
        fail('Sound Forge/training provenance policy mismatch')


def validate_codec_tournament(report: Mapping, codec: str) -> None:
    if int(report.get('schema', 0)) != 2 or not report.get('promotion_pass'):
        fail('Schema 8 requires passed v2 codec tournament')
    if str(report.get('winner_kind', '')).lower() != codec:
        fail('codec tournament winner does not match requested shipping codec')
    if int(report.get('real_anchor_count', 0)) < 8:
        fail('codec tournament requires >=8 real anchors')


def validate_abx_v2(report: Mapping, label: str) -> None:
    if int(report.get('schema', 0)) != 2 or not report.get('transparency_pass'):
        fail(label + ' transparency failed')
    if int(report.get('listener_count', 0)) < 5 or int(report.get('trial_count', 0)) < 60:
        fail(label + ' requires >=5 listeners and >=60 completed trials')
    if report.get('significant_above_chance'):
        fail(label + ' is significantly identifiable above chance')
    accuracy = report.get('accuracy')
    target = float(report.get('target_max_accuracy', .60))
    if accuracy is not None and float(accuracy) > target:
        fail(f'{label} accuracy {accuracy} exceeds target {target}')


def validate_acoustic_segments(report: Mapping) -> None:
    if int(report.get('schema', 0)) != 1 or report.get('segment_version') != 'acoustic_segments_v20' or not report.get('release_pass'):
        fail('acoustic segmentation evidence failed contract')
    if int(report.get('real_segments', 0)) < 1 or int(report.get('modeled_segments', 0)) < 1:
        fail('acoustic segmentation lacks both real and modeled lanes')


def validate_acoustic_promotion(report: Mapping, codec: str) -> str:
    if int(report.get('schema', 0)) != 1 or report.get('promotion_version') != 'acoustic_promotion_v20' or not report.get('promotion_pass'):
        fail('acoustic promotion evidence failed contract')
    if str(report.get('shipping_codec', '')).lower() != codec or str(report.get('winner_kind', '')).lower() != codec:
        fail('acoustic promotion codec does not match requested shipping codec')
    promotion_id = str(report.get('promotion_id', '')).lower()
    if not sha256_like(promotion_id):
        fail('invalid acoustic promotion ID')
    return promotion_id


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--provenance', required=True)
    ap.add_argument('--registry', default=str(Path(__file__).resolve().parents[1] / 'dataset_registry.json'))
    ap.add_argument('--metrics', required=True)
    ap.add_argument('--sound-forge-report', required=True)
    ap.add_argument('--codec-tournament', required=True)
    ap.add_argument('--codec-abx-report', required=True)
    ap.add_argument('--acoustic-segments', required=True)
    ap.add_argument('--generated-real-abx', required=True)
    ap.add_argument('--acoustic-promotion', required=True)
    ap.add_argument('--phrase-curriculum-report', required=True)
    ap.add_argument('--hq-transition-promotion', required=True)
    ap.add_argument('--compact-transition-promotion', required=True)
    ap.add_argument('--hq-checkpoint', required=True, help='Pre-seal HQ checkpoint targeted by the HQ promotion report.')
    ap.add_argument('--compact-checkpoint', required=True, help='Pre-seal Compact/Frontier checkpoint targeted by the Compact promotion report.')
    ap.add_argument('--codec', choices=('dac44', 'strings_vae64'), required=True)
    a = ap.parse_args()

    provenance_path = require_file(a.provenance, 'training provenance')
    registry_path = require_file(a.registry, 'dataset registry')
    metrics_path = require_file(a.metrics, 'release metrics')
    sound_forge_path = require_file(a.sound_forge_report, 'Sound Forge')
    codec_tournament_path = require_file(a.codec_tournament, 'codec tournament')
    codec_abx_path = require_file(a.codec_abx_report, 'codec ABX')
    acoustic_segments_path = require_file(a.acoustic_segments, 'acoustic segments')
    generated_real_abx_path = require_file(a.generated_real_abx, 'generated-real ABX')
    acoustic_promotion_path = require_file(a.acoustic_promotion, 'acoustic promotion')
    curriculum_path = require_file(a.phrase_curriculum_report, 'phrase curriculum')
    hq_promotion_path = require_file(a.hq_transition_promotion, 'HQ transition promotion')
    compact_promotion_path = require_file(a.compact_transition_promotion, 'Compact transition promotion')
    hq_checkpoint = require_file(a.hq_checkpoint, 'HQ candidate checkpoint')
    compact_checkpoint = require_file(a.compact_checkpoint, 'Compact candidate checkpoint')

    provenance = load_json(provenance_path, 'training provenance')
    registry = load_json(registry_path, 'dataset registry')
    metrics = load_json(metrics_path, 'release metrics')
    sound_forge = load_json(sound_forge_path, 'Sound Forge')
    codec_tournament = load_json(codec_tournament_path, 'codec tournament')
    codec_abx = load_json(codec_abx_path, 'codec ABX')
    acoustic_segments = load_json(acoustic_segments_path, 'acoustic segments')
    generated_real_abx = load_json(generated_real_abx_path, 'generated-real ABX')
    acoustic_promotion = load_json(acoustic_promotion_path, 'acoustic promotion')
    curriculum = load_json(curriculum_path, 'phrase curriculum')
    hq_promotion = load_json(hq_promotion_path, 'HQ transition promotion')
    compact_promotion = load_json(compact_promotion_path, 'Compact transition promotion')

    policy = validate_training_policy(provenance)
    used = validate_registry(provenance, registry)
    validate_metrics(metrics)
    validate_sound_forge(sound_forge, policy)
    validate_codec_tournament(codec_tournament, a.codec)
    validate_abx_v2(codec_abx, 'codec ABX')
    validate_acoustic_segments(acoustic_segments)
    validate_abx_v2(generated_real_abx, 'generated-real ABX')
    acoustic_id = validate_acoustic_promotion(acoustic_promotion, a.codec)

    try:
        phrase_attestation = validate_phrase_training_attestation(provenance.get('phrase_supervision'))
    except ValueError as e:
        fail('training provenance phrase supervision invalid: ' + str(e))
    if not phrase_attestation:
        fail('Schema 8 requires training_provenance.phrase_supervision attestation')

    try:
        assert_release_evidence(curriculum, {'hq': hq_promotion, 'compact': compact_promotion})
    except ValueError as e:
        fail('phrase transition evidence failed: ' + str(e))

    curriculum_sha = sha256_file(curriculum_path)
    phrase_index_sha = str(curriculum.get('output_index_sha256', '')).lower()
    if str(phrase_attestation.get('source_index_sha256', '')).lower() != phrase_index_sha:
        fail('training provenance phrase source index does not match curriculum output index')
    if str(phrase_attestation.get('curriculum_report_sha256', '')).lower() != curriculum_sha:
        fail('training provenance phrase curriculum report SHA mismatch')

    hq_candidate_sha = sha256_file(hq_checkpoint)
    compact_candidate_sha = sha256_file(compact_checkpoint)
    if hq_candidate_sha != str(hq_promotion.get('candidate_checkpoint_sha256', '')).lower():
        fail('HQ candidate checkpoint SHA does not match HQ transition promotion')
    if compact_candidate_sha != str(compact_promotion.get('candidate_checkpoint_sha256', '')).lower():
        fail('Compact candidate checkpoint SHA does not match Compact transition promotion')

    print('SCHEMA 8 PREFLIGHT PASS')
    print('codec:', a.codec)
    print('datasets:', ', '.join(sorted(used)))
    print('acoustic_promotion_id:', acoustic_id)
    print('phrase_source_index_sha256:', phrase_index_sha)
    print('phrase_curriculum_sha256:', curriculum_sha)
    print('heldout_index_sha256:', str(hq_promotion.get('heldout_index_sha256', '')).lower())
    print('hq_transition_promotion_id:', str(hq_promotion.get('promotion_id', '')).lower())
    print('compact_transition_promotion_id:', str(compact_promotion.get('promotion_id', '')).lower())
    print('hq_candidate_checkpoint_sha256:', hq_candidate_sha)
    print('compact_candidate_checkpoint_sha256:', compact_candidate_sha)
    print('NOTE: preflight is read-only and does not replace sealing, manifest/gate, GPU evaluation, or listener evidence.')


if __name__ == '__main__':
    main()
