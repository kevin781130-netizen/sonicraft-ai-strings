from __future__ import annotations
"""Dependency-light smoke for the read-only Schema 8 production preflight."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from phrase_release_provenance import build_phrase_training_attestation

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / 'training' / 'scripts' / 'schema8_release_preflight.py'
POLICY = {
    'real_probability': .80,
    'modeled_probability': .20,
    'modeled_timbre_anchor': False,
    'modeled_adversarial_target': False,
    'curriculum': 'lane_locked_acoustic_promotion_v20',
    'cleanroom_modeled_only': True,
}


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], expected: int) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, env=os.environ.copy())
    if p.returncode != expected:
        raise AssertionError(
            f'unexpected return code {p.returncode}, expected {expected}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}'
        )
    return p


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        registry = d / 'registry.json'
        write_json(registry, {
            'real_fixture': {'commercial_safe': True, 'release_blocked': False},
            'modeled_fixture': {'commercial_safe': True, 'release_blocked': False},
        })

        phrase_index = d / 'phrase_finetune.jsonl'
        phrase_index.write_text('{"fixture":"phrase-finetune"}\n', encoding='utf-8')
        phrase_index_sha = sha(phrase_index)
        curriculum = d / 'curriculum.json'
        write_json(curriculum, {
            'version': 'phrase_finetune_index_v1',
            'output_index_sha256': phrase_index_sha,
            'curriculum_sweep': {
                '0.0': {'modeled_probability': .20, 'phrase_share_within_modeled': .50},
                '0.5': {'modeled_probability': .20, 'phrase_share_within_modeled': .50},
                '1.0': {'modeled_probability': .20, 'phrase_share_within_modeled': .50},
            },
        })

        provenance = d / 'provenance.json'
        write_json(provenance, {
            'datasets': ['real_fixture', 'modeled_fixture'],
            'training_policy': POLICY,
            'phrase_supervision': build_phrase_training_attestation(phrase_index_sha, sha(curriculum)),
        })

        metrics = d / 'metrics.json'
        write_json(metrics, {
            'product': 'SONICRAFT AI Strings Q4', 'release_pass': True,
            'midi_lock_pass': True, 'vibrato_monotonic_pass': True,
            'tempo_transition_pass': True, 'dropout_fallback_pass': True, 'abx_pass': True,
            'abx': {'generated_identification_accuracy': .50, 'target_max_accuracy': .60, 'listener_count': 5, 'trial_count': 60},
        })

        sound_forge = d / 'sound_forge.json'
        write_json(sound_forge, {
            'schema': 1, 'forge_version': 'sound_forge_v19', 'release_pass': True,
            'eligible_real_files': 1, 'eligible_modeled_files': 1,
            'rights_failures': 0, 'audio_failures': 0, 'training_policy': POLICY,
        })
        codec_tournament = d / 'codec_tournament.json'
        write_json(codec_tournament, {
            'schema': 2, 'metric_family': 'stereo_phase_harmonic_strings_v20',
            'promotion_pass': True, 'winner_kind': 'strings_vae64', 'real_anchor_count': 8,
        })
        codec_abx = d / 'codec_abx.json'
        write_json(codec_abx, {
            'schema': 2, 'transparency_pass': True, 'listener_count': 5, 'trial_count': 60,
            'significant_above_chance': False, 'accuracy': .50, 'target_max_accuracy': .60,
        })
        acoustic_segments = d / 'acoustic_segments.json'
        write_json(acoustic_segments, {
            'schema': 1, 'segment_version': 'acoustic_segments_v20', 'release_pass': True,
            'real_segments': 1, 'modeled_segments': 1,
        })
        generated_real_abx = d / 'generated_real_abx.json'
        write_json(generated_real_abx, {
            'schema': 2, 'transparency_pass': True, 'listener_count': 5, 'trial_count': 60,
            'significant_above_chance': False, 'accuracy': .50, 'target_max_accuracy': .60,
        })
        acoustic_promotion = d / 'acoustic_promotion.json'
        write_json(acoustic_promotion, {
            'schema': 1, 'promotion_version': 'acoustic_promotion_v20', 'promotion_pass': True,
            'shipping_codec': 'strings_vae64', 'winner_kind': 'strings_vae64', 'promotion_id': 'b' * 64,
        })

        heldout_index = d / 'heldout.jsonl'
        heldout_index.write_text('{"fixture":"heldout"}\n', encoding='utf-8')
        heldout = sha(heldout_index)
        hq_checkpoint = d / 'hq.pt'; hq_checkpoint.write_bytes(b'hq pre-seal fixture')
        compact_checkpoint = d / 'compact.pt'; compact_checkpoint.write_bytes(b'compact pre-seal fixture')
        hq_promotion = d / 'hq_transition.json'
        compact_promotion = d / 'compact_transition.json'
        write_json(hq_promotion, {
            'schema': 1, 'promotion_version': 'transition_promotion_v1', 'promotion_pass': True,
            'promotion_id': 'd' * 64, 'candidate_checkpoint_sha256': sha(hq_checkpoint),
            'heldout_index_sha256': heldout, 'sample_count': 64,
        })
        write_json(compact_promotion, {
            'schema': 1, 'promotion_version': 'transition_promotion_v1', 'promotion_pass': True,
            'promotion_id': 'e' * 64, 'candidate_checkpoint_sha256': sha(compact_checkpoint),
            'heldout_index_sha256': heldout, 'sample_count': 64,
        })

        common = [
            sys.executable, str(PREFLIGHT),
            '--provenance', str(provenance), '--registry', str(registry), '--metrics', str(metrics),
            '--sound-forge-report', str(sound_forge), '--codec-tournament', str(codec_tournament),
            '--codec-abx-report', str(codec_abx), '--acoustic-segments', str(acoustic_segments),
            '--generated-real-abx', str(generated_real_abx), '--acoustic-promotion', str(acoustic_promotion),
            '--phrase-curriculum-report', str(curriculum), '--phrase-finetune-index', str(phrase_index),
            '--hq-transition-promotion', str(hq_promotion), '--compact-transition-promotion', str(compact_promotion),
            '--hq-checkpoint', str(hq_checkpoint), '--compact-checkpoint', str(compact_checkpoint),
            '--codec', 'strings_vae64',
        ]

        passed = run(common + ['--heldout-index', str(heldout_index)], 0)
        assert 'SCHEMA 8 PREFLIGHT PASS' in passed.stdout

        wrong_heldout = d / 'wrong_heldout.jsonl'; wrong_heldout.write_text('{"fixture":"wrong-heldout"}\n', encoding='utf-8')
        stale = run(common + ['--heldout-index', str(wrong_heldout)], 1)
        assert 'held-out transition index SHA does not match renderer promotion reports' in (stale.stdout + stale.stderr)

        wrong_compact = d / 'wrong_compact.pt'; wrong_compact.write_bytes(b'wrong checkpoint')
        wrong_checkpoint_args = [x for x in common]
        idx = wrong_checkpoint_args.index('--compact-checkpoint')
        wrong_checkpoint_args[idx + 1] = str(wrong_compact)
        failed = run(wrong_checkpoint_args + ['--heldout-index', str(heldout_index)], 1)
        assert 'Compact candidate checkpoint SHA does not match Compact transition promotion' in (failed.stdout + failed.stderr)

    print('schema8 release preflight smoke: PASS')


if __name__ == '__main__':
    main()
