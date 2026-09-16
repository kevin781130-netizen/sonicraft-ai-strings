from __future__ import annotations
"""Dependency-light end-to-end dry run for the Schema 8 manifest + commercial gate.

The fixture uses tiny JSON checkpoint dictionaries and a local torch stub. It tests
release-contract control flow only; it is not a model/tensor numerical test.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from phrase_provenance import build_phrase_provenance
from phrase_release_provenance import build_phrase_training_attestation

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / 'training'
SCRIPTS = TRAINING / 'scripts'
CURRICULUM = 'lane_locked_acoustic_promotion_v20'
POLICY = {
    'real_probability': 0.80,
    'modeled_probability': 0.20,
    'modeled_timbre_anchor': False,
    'modeled_adversarial_target': False,
    'curriculum': CURRICULUM,
    'cleanroom_modeled_only': True,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def run_checked(args: list[str], env: dict[str, str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
    if p.returncode != expected:
        raise AssertionError(
            f'command returned {p.returncode}, expected {expected}: {args}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}'
        )
    return p


def checkpoint_base(acoustic_id: str) -> dict:
    return {
        'model': {},
        'ema': {},
        'training_mix': {'real': 0.80, 'modeled': 0.20, 'curriculum': CURRICULUM},
        'acoustic_promotion_id': acoustic_id,
        'acoustic_promotion_seal': {
            'schema': 1,
            'promotion_id': acoustic_id,
            'tensor_sha256': 'a' * 64,
        },
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        evidence = work / 'evidence'
        models = work / 'Models'
        stub = work / 'stub'
        evidence.mkdir(); models.mkdir(); stub.mkdir()

        # torch.load is the only torch API needed by this metadata-only fixture;
        # tensor_digest sees empty model dictionaries, so is_tensor is never true.
        (stub / 'torch.py').write_text(
            "import json\nfrom pathlib import Path\n"
            "def load(path, map_location=None, weights_only=False):\n"
            "    return json.loads(Path(path).read_text(encoding='utf-8'))\n"
            "def is_tensor(value):\n    return False\n",
            encoding='utf-8',
        )
        env = os.environ.copy()
        env['PYTHONPATH'] = str(stub) + os.pathsep + str(TRAINING) + os.pathsep + env.get('PYTHONPATH', '')

        phrase_index = work / 'phrase_finetune.jsonl'
        phrase_rows = [{
            'file': 'dummy_phrase.npz',
            'dataset': 'synthetic_cleanroom_bowed_v18',
            'training_origin': 'modeled',
            'phrase_family': 'portamento_pair',
        }]
        phrase_index.write_text(json.dumps(phrase_rows[0], sort_keys=True) + '\n', encoding='utf-8')
        hq_phrase = build_phrase_provenance(phrase_rows, phrase_index)
        phrase_root_sha = hq_phrase['phrase_source_index_sha256']

        compact_index = work / 'compact_anchor.jsonl'
        compact_rows = [{'file': 'dummy_real.npz', 'dataset': 'iowa_mis', 'training_origin': 'real'}]
        compact_index.write_text(json.dumps(compact_rows[0], sort_keys=True) + '\n', encoding='utf-8')
        compact_phrase = build_phrase_provenance(compact_rows, compact_index, hq_phrase)

        curriculum = {
            'version': 'phrase_finetune_index_v1',
            'output_index_sha256': phrase_root_sha,
            'curriculum_sweep': {
                '0.0': {'modeled_probability': 0.20, 'phrase_share_within_modeled': 0.55},
                '0.5': {'modeled_probability': 0.20, 'phrase_share_within_modeled': 0.55},
                '1.0': {'modeled_probability': 0.20, 'phrase_share_within_modeled': 0.55},
            },
        }
        curriculum_path = evidence / 'phrase_curriculum.json'
        write_json(curriculum_path, curriculum)
        curriculum_sha = sha256_file(curriculum_path)

        phrase_attestation = build_phrase_training_attestation(phrase_root_sha, curriculum_sha)
        provenance = {
            'datasets': ['iowa_mis', 'synthetic_cleanroom_bowed_v18'],
            'training_policy': POLICY,
            'phrase_supervision': phrase_attestation,
        }
        provenance_path = evidence / 'training_provenance.json'
        write_json(provenance_path, provenance)

        metrics_path = evidence / 'release_metrics.json'
        write_json(metrics_path, {
            'product': 'SONICRAFT AI Strings Q4',
            'release_pass': True,
            'midi_lock_pass': True,
            'vibrato_monotonic_pass': True,
            'tempo_transition_pass': True,
            'dropout_fallback_pass': True,
            'abx_pass': True,
            'abx': {
                'generated_identification_accuracy': 0.50,
                'target_max_accuracy': 0.60,
                'listener_count': 5,
                'trial_count': 60,
            },
        })

        sound_forge = evidence / 'sound_forge.json'
        write_json(sound_forge, {
            'schema': 1, 'forge_version': 'sound_forge_v19', 'release_pass': True,
            'eligible_real_files': 1, 'eligible_modeled_files': 1,
            'rights_failures': 0, 'audio_failures': 0, 'training_policy': POLICY,
        })
        codec_tournament = evidence / 'codec_tournament.json'
        write_json(codec_tournament, {
            'schema': 2, 'metric_family': 'stereo_phase_harmonic_strings_v20',
            'promotion_pass': True, 'winner': 'fixture', 'winner_kind': 'strings_vae64',
            'real_anchor_count': 8,
        })
        codec_abx = evidence / 'codec_abx.json'
        write_json(codec_abx, {
            'schema': 2, 'transparency_pass': True, 'listener_count': 5, 'trial_count': 60,
            'significant_above_chance': False, 'accuracy': 0.50, 'target_max_accuracy': 0.60,
        })
        acoustic_segments = evidence / 'acoustic_segments.json'
        write_json(acoustic_segments, {
            'schema': 1, 'segment_version': 'acoustic_segments_v20', 'release_pass': True,
            'real_segments': 1, 'modeled_segments': 1,
        })
        generated_real_abx = evidence / 'generated_real_abx.json'
        write_json(generated_real_abx, {
            'schema': 2, 'transparency_pass': True, 'listener_count': 5, 'trial_count': 60,
            'significant_above_chance': False, 'accuracy': 0.50,
        })
        acoustic_id = '1' * 64
        acoustic_promotion = evidence / 'acoustic_promotion.json'
        write_json(acoustic_promotion, {
            'schema': 1, 'promotion_version': 'acoustic_promotion_v20', 'promotion_pass': True,
            'shipping_codec': 'strings_vae64', 'winner_kind': 'strings_vae64',
            'promotion_id': acoustic_id,
        })

        heldout_sha = '4' * 64
        hq_pid, compact_pid = '2' * 64, '3' * 64
        hq_transition = evidence / 'transition_hq.json'
        compact_transition = evidence / 'transition_compact.json'
        write_json(hq_transition, {
            'schema': 1, 'promotion_version': 'transition_promotion_v1', 'promotion_pass': True,
            'promotion_id': hq_pid, 'candidate_checkpoint_sha256': '5' * 64,
            'heldout_index_sha256': heldout_sha, 'sample_count': 64,
        })
        write_json(compact_transition, {
            'schema': 1, 'promotion_version': 'transition_promotion_v1', 'promotion_pass': True,
            'promotion_id': compact_pid, 'candidate_checkpoint_sha256': '6' * 64,
            'heldout_index_sha256': heldout_sha, 'sample_count': 64,
        })
        empty_tensor_digest = hashlib.sha256(b'').hexdigest()

        hq_ck = checkpoint_base(acoustic_id)
        hq_ck.update({
            'phrase_finetune_provenance': hq_phrase,
            'transition_promotion_id': hq_pid,
            'transition_promotion_seal': {
                'schema': 1, 'promotion_id': hq_pid,
                'promotion_sha256': sha256_file(hq_transition),
                'candidate_checkpoint_sha256': '5' * 64,
                'curriculum_sha256': curriculum_sha,
                'heldout_index_sha256': heldout_sha,
                'tensor_sha256': empty_tensor_digest,
            },
        })
        compact_ck = checkpoint_base(acoustic_id)
        compact_ck.update({
            'phrase_finetune_provenance': compact_phrase,
            'transition_promotion_id': compact_pid,
            'transition_promotion_seal': {
                'schema': 1, 'promotion_id': compact_pid,
                'promotion_sha256': sha256_file(compact_transition),
                'candidate_checkpoint_sha256': '6' * 64,
                'curriculum_sha256': curriculum_sha,
                'heldout_index_sha256': heldout_sha,
                'tensor_sha256': empty_tensor_digest,
            },
        })
        decoder_ck = checkpoint_base(acoustic_id)
        decoder_ck['decoder'] = {}

        hq_path = models / 'ballad_renderer_hq_v20_best.pt'
        compact_path = models / 'ballad_renderer_frontier_v20_shortcut.pt'
        decoder_path = models / 'strings_vae64_decoder_v20.pt'
        write_json(hq_path, hq_ck); write_json(compact_path, compact_ck); write_json(decoder_path, decoder_ck)

        builder = str(SCRIPTS / 'build_release_model_manifest.py')
        common_builder = [
            sys.executable, builder,
            '--model-dir', str(models), '--provenance', str(provenance_path), '--metrics', str(metrics_path),
            '--codec', 'strings_vae64', '--sound-forge-report', str(sound_forge),
            '--codec-tournament', str(codec_tournament), '--codec-abx-report', str(codec_abx),
            '--acoustic-segments', str(acoustic_segments), '--generated-real-abx', str(generated_real_abx),
            '--acoustic-promotion', str(acoustic_promotion),
        ]

        # The independent training provenance must already prevent a Schema 7 build.
        downgrade_build = run_checked(common_builder + ['--schema', '7'], env, expected=1)
        assert 'Release Schema 8 is required' in (downgrade_build.stdout + downgrade_build.stderr)

        build = run_checked(common_builder + [
            '--schema', '8', '--phrase-curriculum-report', str(curriculum_path),
            '--hq-transition-promotion', str(hq_transition),
            '--compact-transition-promotion', str(compact_transition), '--approve',
        ], env)
        assert 'WROTE' in build.stdout

        manifest_path = models / 'release_model_manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        assert manifest['schema'] == 8
        assert manifest['phrase_source_index_sha256'] == phrase_root_sha
        assert manifest['phrase_training_attestation_id'] == phrase_attestation['attestation_id']

        gate = [sys.executable, str(SCRIPTS / 'commercial_release_gate.py'), '--root', str(ROOT), '--model-dir', str(models)]
        passed_gate = run_checked(gate, env)
        assert 'COMMERCIAL RELEASE GATE PASS' in passed_gate.stdout

        # Simulate stripping checkpoint phrase markers and hand-editing the manifest to
        # Schema 7. Update file hashes so the model-integrity check itself still passes;
        # the independent training provenance must be the reason this release is refused.
        for path in (hq_path, compact_path):
            ck = json.loads(path.read_text(encoding='utf-8'))
            ck.pop('phrase_finetune_provenance', None)
            write_json(path, ck)
        manifest['schema'] = 7
        for entry in manifest['files']:
            if entry['role'] == 'hq': target = hq_path
            elif entry['role'] == 'compact': target = compact_path
            else: continue
            entry['sha256'] = sha256_file(target)
            entry['bytes'] = target.stat().st_size
            entry.pop('phrase_provenance_id', None)
            entry.pop('phrase_source_index_sha256', None)
        write_json(manifest_path, manifest)
        refused = run_checked(gate, env, expected=2)
        assert 'training provenance declares phrase supervision; Release Schema 8 is required' in refused.stdout

    print('schema8 end-to-end release contract smoke: PASS')


if __name__ == '__main__':
    main()
