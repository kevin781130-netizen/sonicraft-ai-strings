from __future__ import annotations
"""Stamp phrase supervision into training_provenance.json from curriculum evidence."""
import argparse, hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phrase_release_provenance import build_phrase_training_attestation
from release_transition_gate import curriculum_reasons


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--provenance', required=True, help='Existing training_provenance.json')
    ap.add_argument('--curriculum-report', required=True)
    ap.add_argument('--out', help='Defaults to replacing --provenance')
    a = ap.parse_args()

    prov_path = Path(a.provenance)
    report_path = Path(a.curriculum_report)
    out_path = Path(a.out) if a.out else prov_path

    prov = json.loads(prov_path.read_text(encoding='utf-8'))
    report = json.loads(report_path.read_text(encoding='utf-8'))
    reasons = curriculum_reasons(report)
    if reasons:
        raise SystemExit('invalid phrase curriculum report: ' + '; '.join(reasons))

    attestation = build_phrase_training_attestation(
        str(report.get('output_index_sha256', '')),
        sha256_file(report_path),
    )
    prov['phrase_supervision'] = attestation
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(prov, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('WROTE', out_path)
    print('phrase source index:', attestation['source_index_sha256'])
    print('phrase attestation:', attestation['attestation_id'])


if __name__ == '__main__':
    main()
