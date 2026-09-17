from __future__ import annotations
"""Dependency-light smoke for independent phrase training provenance."""
from phrase_release_provenance import (
    build_phrase_training_attestation,
    validate_phrase_training_attestation,
)

HEX_A = 'a' * 64
HEX_B = 'b' * 64


def main() -> None:
    att = build_phrase_training_attestation(HEX_A, HEX_B)
    checked = validate_phrase_training_attestation(att)
    assert checked and checked['enabled']
    assert checked['required_release_schema'] == 8
    assert checked['source_index_sha256'] == HEX_A
    assert checked['curriculum_report_sha256'] == HEX_B

    tampered = dict(att)
    tampered['source_index_sha256'] = 'c' * 64
    try:
        validate_phrase_training_attestation(tampered)
    except ValueError:
        pass
    else:
        raise AssertionError('tampered phrase training attestation unexpectedly validated')

    assert validate_phrase_training_attestation(None) is None
    assert validate_phrase_training_attestation({'enabled': False}) is None
    print('phrase release provenance smoke: PASS')


if __name__ == '__main__':
    main()
