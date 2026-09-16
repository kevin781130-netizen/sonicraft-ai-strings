from __future__ import annotations
"""Dependency-light smoke checks for Schema 8 phrase transition evidence."""
from release_transition_gate import release_evidence_reasons

HEX_A='a'*64
HEX_B='b'*64
HEX_C='c'*64
HEX_D='d'*64


def curriculum(modeled=.20, phrase=.55):
    return {
        'version':'phrase_finetune_index_v1',
        'curriculum_sweep':{
            '0.0':{'modeled_probability':modeled,'phrase_share_within_modeled':phrase},
            '0.5':{'modeled_probability':modeled,'phrase_share_within_modeled':phrase},
            '1.0':{'modeled_probability':modeled,'phrase_share_within_modeled':phrase},
        },
    }


def promotion(pid,candidate,heldout=HEX_C,passed=True):
    return {
        'schema':1,'promotion_version':'transition_promotion_v1','promotion_id':pid,
        'promotion_pass':passed,'candidate_checkpoint_sha256':candidate,
        'heldout_index_sha256':heldout,'sample_count':64,
    }


def main():
    good={'hq':promotion(HEX_A,HEX_D),'compact':promotion(HEX_B,'e'*64)}
    assert release_evidence_reasons(curriculum(),good)==[]

    same_id={'hq':promotion(HEX_A,HEX_D),'compact':promotion(HEX_A,'e'*64)}
    assert 'renderer_transition_promotion_ids_not_checkpoint_specific' in release_evidence_reasons(curriculum(),same_id)

    mismatch={'hq':promotion(HEX_A,HEX_D,HEX_C),'compact':promotion(HEX_B,'e'*64,'f'*64)}
    assert 'renderer_transition_heldout_index_mismatch' in release_evidence_reasons(curriculum(),mismatch)

    drift=release_evidence_reasons(curriculum(modeled=.24),good)
    assert any(x.startswith('phrase_curriculum_modeled_lane_drift_') for x in drift)

    failed={'hq':promotion(HEX_A,HEX_D,passed=False),'compact':promotion(HEX_B,'e'*64)}
    assert 'hq_transition_promotion_failed' in release_evidence_reasons(curriculum(),failed)
    print('schema8 release transition smoke: PASS')


if __name__=='__main__': main()
