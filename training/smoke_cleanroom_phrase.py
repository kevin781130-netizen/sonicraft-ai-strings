from __future__ import annotations
"""Smoke test for clean-room multi-note phrase generation."""
from pathlib import Path
import json
import tempfile
import numpy as np

from scripts.generate_cleanroom_phrase_corpus import PHRASE_FAMILIES, build_phrase_corpus


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='sonicraft_phrase_') as td:
        out = Path(td) / 'phrases'
        report = build_phrase_corpus(
            out_dir=out,
            count=len(PHRASE_FAMILIES) * 2,
            seconds=0.8,
            sample_rate=48000,
            seed=4242,
            section_prob=0.0,
        )
        assert report['accepted'] > 0
        rows = [
            json.loads(x)
            for x in (out / 'index.jsonl').read_text(encoding='utf-8').splitlines()
            if x.strip()
        ]
        assert rows
        assert all(r['dataset'] == 'synthetic_cleanroom_bowed_v18' for r in rows)
        assert all(r['proprietary_model_bytes_embedded'] is False for r in rows)
        assert {r['phrase_family'] for r in rows}.issubset(set(PHRASE_FAMILIES))
        for row in rows[:3]:
            with np.load(row['control_curves'], allow_pickle=False) as data:
                for key in ('pitch','gate','onset','articulation_curve'):
                    assert key in data.files
                assert len(data['pitch']) == 80
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
