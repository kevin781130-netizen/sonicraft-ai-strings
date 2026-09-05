from instrument_x_cleanroom import decode_flags,PerformancePolicy,apply_targeted_retake,RETAKE_MICROPITCH,RETAKE_TIMING,RETAKE_BOW_ATTACK,RETAKE_ALL
from stage_renderer_np import stage_bundle_np,MIC_NAMES
import numpy as np

def flags(authority=True,phrase=True,loose=.2,target=7):
    return 2|(5<<2)|(1<<5)|(1<<6)|(1<<7)|((target&7)<<8)|(9<<11)|(2<<19)|(12<<21)|(1<<25)|(int(authority)<<26)|(int(phrase)<<27)|(int(round(loose*15))<<28)
p=decode_flags(flags())
assert p.retake_target==7 and p.midi_authority_lock and p.phrase_director and p.multi_out
assert len(MIC_NAMES)==16
x=stage_bundle_np(np.zeros(480,np.float32),48000,.2,1); assert x.shape==(480,34)
n=128;base={'dynamics':np.full(n,.5,np.float32),'attack_character':np.full(n,.5,np.float32),'short_tightness':np.full(n,.5,np.float32),'bow_change_prob':np.full(n,.2,np.float32),'vibrato_onset':np.zeros(n,np.float32),'vibrato_jitter':np.zeros(n,np.float32),'pitchbend':np.full(n,.5,np.float32),'transition_speed':np.full(n,.5,np.float32),'timing_feel':np.zeros(n,np.float32)}
q=apply_targeted_retake(base,'x',0,PerformancePolicy(retake_target=RETAKE_MICROPITCH,retake_nonce=1,retake_amount=1,midi_authority_lock=True));assert np.array_equal(q['pitchbend'],base['pitchbend'])
q=apply_targeted_retake(base,'x',0,PerformancePolicy(retake_target=RETAKE_MICROPITCH,retake_nonce=1,retake_amount=1,midi_authority_lock=False));assert np.max(np.abs(q['pitchbend']-base['pitchbend']))>0
q=apply_targeted_retake(base,'x',0,PerformancePolicy(retake_target=RETAKE_TIMING,retake_nonce=2,retake_amount=1));assert np.max(np.abs(q['transition_speed']-base['transition_speed']))>0
q=apply_targeted_retake(base,'x',0,PerformancePolicy(retake_target=RETAKE_BOW_ATTACK,retake_nonce=3,retake_amount=1));assert np.max(np.abs(q['attack_character']-base['attack_character']))>0
print('SONICRAFT v2.8 runtime Performance Commander smoke OK')
