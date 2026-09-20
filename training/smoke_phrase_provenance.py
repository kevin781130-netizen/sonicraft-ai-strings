from __future__ import annotations
"""Dependency-light smoke test for transitive phrase checkpoint provenance."""
import json, tempfile
from pathlib import Path
from phrase_provenance import build_phrase_provenance, validate_checkpoint_phrase_provenance


def main():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        phrase_index=root/'phrase.jsonl'
        phrase_rows=[{
            'file':'dummy.npz','dataset':'synthetic_cleanroom_bowed_v18',
            'training_origin':'modeled','phrase_family':'portamento_pair',
        }]
        phrase_index.write_text(json.dumps(phrase_rows[0])+'\n',encoding='utf-8')
        parent=build_phrase_provenance(phrase_rows,phrase_index)
        checked=validate_checkpoint_phrase_provenance({'phrase_finetune_provenance':parent})
        assert checked and checked['enabled'] and checked['required_release_schema']==8
        assert checked['phrase_source_index_sha256']==checked['source_index_sha256']
        assert checked['phrase_families']==['portamento_pair']

        base_index=root/'base.jsonl'
        base_rows=[{'file':'base.npz','dataset':'custom_owned_session','training_origin':'real'}]
        base_index.write_text(json.dumps(base_rows[0])+'\n',encoding='utf-8')
        child=build_phrase_provenance(base_rows,base_index,parent)
        checked_child=validate_checkpoint_phrase_provenance({'phrase_finetune_provenance':child})
        assert checked_child['enabled']
        assert checked_child['inherited_from_parent']
        assert checked_child['local_phrase_row_count']==0
        assert checked_child['phrase_source_index_sha256']==parent['phrase_source_index_sha256']
        assert checked_child['phrase_families']==parent['phrase_families']
        assert checked_child['parent_provenance_id']==parent['provenance_id']

        tampered=dict(child);tampered['phrase_families']=['forged_family']
        try:
            validate_checkpoint_phrase_provenance({'phrase_finetune_provenance':tampered})
        except ValueError:
            pass
        else:
            raise AssertionError('tampered phrase provenance unexpectedly validated')

    print('phrase provenance smoke: PASS')


if __name__=='__main__': main()
