from __future__ import annotations
"""Dependency-light contract test for transition sealing phrase/curriculum binding."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from phrase_provenance import build_phrase_provenance

ROOT = Path(__file__).resolve().parents[1]
TRAINING = ROOT / 'training'
SEALER = TRAINING / 'scripts' / 'seal_transition_promotion.py'


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, env, expected):
    p = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
    if p.returncode != expected:
        raise AssertionError(f'unexpected return code {p.returncode}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}')
    return p


def curriculum(output_sha: str) -> dict:
    return {
        'version': 'phrase_finetune_index_v1',
        'output_index_sha256': output_sha,
        'curriculum_sweep': {
            '0.0': {'modeled_probability': .20, 'phrase_share_within_modeled': .50},
            '0.5': {'modeled_probability': .20, 'phrase_share_within_modeled': .50},
            '1.0': {'modeled_probability': .20, 'phrase_share_within_modeled': .50},
        },
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        stub = d / 'stub'; stub.mkdir()
        (stub / 'torch.py').write_text(
            "import json\nfrom pathlib import Path\n"
            "def load(path, map_location=None, weights_only=False):\n"
            "    return json.loads(Path(path).read_text(encoding='utf-8'))\n"
            "def save(value, path):\n"
            "    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
            "def is_tensor(value):\n    return False\n",
            encoding='utf-8',
        )
        env = os.environ.copy()
        env['PYTHONPATH'] = str(stub) + os.pathsep + str(TRAINING) + os.pathsep + env.get('PYTHONPATH', '')

        index = d / 'phrase.jsonl'
        rows = [{'file': 'x.npz', 'dataset': 'synthetic_cleanroom_bowed_v18', 'training_origin': 'modeled', 'phrase_family': 'legato_scale'}]
        index.write_text(json.dumps(rows[0]) + '\n', encoding='utf-8')
        marker = build_phrase_provenance(rows, index)
        root_sha = marker['phrase_source_index_sha256']

        checkpoint = d / 'candidate.pt'
        write_json(checkpoint, {'model': {}, 'ema': {}, 'phrase_finetune_provenance': marker})
        promotion = d / 'promotion.json'
        write_json(promotion, {
            'schema': 1, 'promotion_version': 'transition_promotion_v1', 'promotion_pass': True,
            'promotion_id': 'a' * 64, 'candidate_checkpoint_sha256': sha(checkpoint),
            'heldout_index_sha256': 'b' * 64, 'sample_count': 64,
        })

        bad = d / 'bad_curriculum.json'; write_json(bad, curriculum('c' * 64))
        failed = run([sys.executable, str(SEALER), '--checkpoint', str(checkpoint), '--promotion', str(promotion), '--curriculum', str(bad)], env, 1)
        assert 'checkpoint phrase lineage does not match curriculum output index' in (failed.stdout + failed.stderr)

        good = d / 'good_curriculum.json'; write_json(good, curriculum(root_sha))
        passed = run([sys.executable, str(SEALER), '--checkpoint', str(checkpoint), '--promotion', str(promotion), '--curriculum', str(good)], env, 0)
        assert 'TRANSITION SEALED' in passed.stdout
        sealed = json.loads(checkpoint.read_text(encoding='utf-8'))
        assert sealed['transition_promotion_seal']['phrase_source_index_sha256'] == root_sha

    print('transition sealer contract smoke: PASS')


if __name__ == '__main__':
    main()
