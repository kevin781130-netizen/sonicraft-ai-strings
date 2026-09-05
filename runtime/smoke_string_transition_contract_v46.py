from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
score=(ROOT/'runtime/score_expression_graph_v40.py').read_text(encoding='utf-8')
graph=(ROOT/'runtime/string_transition_graph_v46.py').read_text(encoding='utf-8')
runtime=(ROOT/'runtime/string_transition_runtime_v46.py').read_text(encoding='utf-8')
comp=(ROOT/'runtime/compile_musicxml_strings_v46.py').read_text(encoding='utf-8')
npb=(ROOT/'runtime/control_builder_np.py').read_text(encoding='utf-8')
tb=(ROOT/'runtime/model_backend.py').read_text(encoding='utf-8')
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ph=(ROOT/'src/preview_engine.h').read_text(encoding='utf-8')
pcpp=(ROOT/'src/preview_engine.cpp').read_text(encoding='utf-8')
cm=(ROOT/'CMakeLists.txt').read_text(encoding='utf-8')

for token in ['transition_in_link_id','transition_out_link_id','transition_duration_ms','transition_continuity','transition_flags']:
    assert token in score,token
assert any(x in score for x in ['schema":8','schema":9','schema":10'])

for token in ['build_continuous_transition_graph_v46','same-string-portamento','same-bow-legato-shift',
              '_anchor_blend','continuous_transition_out','bow_continuity','portamento_path']:
    assert token in graph,token

for token in ['apply_continuous_transition_paths_v46','multi_note_gesture_active_v46',
              'apply_micro_pitch_conditioning_v46','transition_target_ms' if False else 'target_ms',
              'pitch[left:right]','onset[b:min(len(onset),b+2)]=0.0']:
    assert token in runtime,token
assert 'if not multi_note_gesture_active_v46' in runtime

assert 'apply_continuous_transition_paths_v46' in npb and 'apply_continuous_transition_paths_v46' in tb
assert 'transition_target_ms=trans_ms' in npb and 'transition_target_ms=T(trans_ms)' in tb

for token in ['transition_json','new_midi_cc_or_paramids','CC38 stays non-zero across connected notes',
              'if not n.transition_in_link_id','if not n.transition_out_link_id']:
    assert token in comp,token

# v4.6 adds no new MIDI automation family.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
assert max(v for _,v in pairs)==740
assert 'kParamVoiceGestureAmountBase = 720' in ids and 'kParamVoiceMicroPitchBase = 740' in ids
assert 'kParamVoiceTransition' not in ids or 'kParamVoiceTransitionBase = 460' in ids

# Preview gets explicit continuity without changing Shadow/HQ raw CC39.
assert 'continuousGesture=false' in ph
assert 'if(control.continuousGesture)' in pcpp
assert 'previewGesturePitchBendV46' in proc
assert 'pc.continuousGesture=o.gestureAmount>.0001f' in proc

# State remains v13; transition graph lives in score/MIDI.
assert 'constexpr int kStateVersion = 13;' in proc
assert any(x in cm for x in ['VERSION 4.6.0','VERSION 4.7.0','VERSION 4.8.0','VERSION 4.9.0','VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftStringTransitionSmokeV46' in cm
print('SONICRAFT v4.6 Continuous Transition source contract OK')
