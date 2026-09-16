from __future__ import annotations
"""Dependency-light smoke test for phrase lane weighting + transition gate."""
from phrase_curriculum import curriculum_sweep_audit, with_phrase_lane_weights
from transition_promotion import build_transition_promotion


def main():
    registry={
        'real_test':{'training_origin':'real','source_weight':1.0},
        'synthetic_cleanroom_bowed_v18':{'training_origin':'modeled','source_weight':1.0},
    }
    rows=[]
    for i in range(16): rows.append({'dataset':'real_test','training_origin':'real','instrument':i%4,'articulation':i%4})
    for i in range(8): rows.append({'dataset':'synthetic_cleanroom_bowed_v18','training_origin':'modeled','instrument':i%4,'articulation':i%4})
    families=('legato_scale','portamento_pair','spiccato_pattern','tremolo_sustain','expressive_arc','mixed_bowing')
    for i in range(24): rows.append({'dataset':'synthetic_cleanroom_bowed_v18','training_origin':'modeled','instrument':i%4,'articulation':i%6,'phrase_family':families[i%len(families)]})
    weighted=with_phrase_lane_weights(rows,registry,target_modeled_phrase_share=.65)
    sweep=curriculum_sweep_audit(weighted,registry)
    for audit in sweep.values():
        assert abs(audit['modeled_probability']-.20)<1e-6, audit
        assert audit['phrase_share_within_modeled']>.45, audit
    curriculum={'version':'phrase_finetune_index_v1','curriculum_sweep':sweep}
    baseline={'schema':1,'version':'renderer_transition_eval_v1','sample_count':96,'index_sha256':'a'*64,'seed':17,'checkpoint_sha256':'b'*64,
              'metrics':{'flow':1.0,'continuity':1.0,'accel':1.0}}
    candidate={'schema':1,'version':'renderer_transition_eval_v1','sample_count':96,'index_sha256':'a'*64,'seed':17,'checkpoint_sha256':'c'*64,
               'metrics':{'flow':1.005,'continuity':.965,'accel':.99}}
    good=build_transition_promotion(baseline,candidate,curriculum)
    assert good['promotion_pass'],good
    bad=dict(candidate);bad['metrics']={'flow':1.10,'continuity':1.02,'accel':1.08}
    rejected=build_transition_promotion(baseline,bad,curriculum)
    assert not rejected['promotion_pass'],rejected
    print('phrase curriculum + transition promotion smoke PASS',good['promotion_id'])

if __name__=='__main__':main()
