from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
score=(ROOT/'runtime/score_expression_graph_v40.py').read_text();graph=(ROOT/'runtime/string_gesture_graph_v45.py').read_text();rt=(ROOT/'runtime/string_gesture_runtime_v45.py').read_text();comp=(ROOT/'runtime/compile_musicxml_strings_v45.py').read_text();ids=(ROOT/'src/ids.h').read_text();proc=(ROOT/'src/processor.cpp').read_text();ctl=(ROOT/'src/controller.cpp').read_text();ph=(ROOT/'src/processor.h').read_text();npb=(ROOT/'runtime/control_builder_np.py').read_text();tb=(ROOT/'runtime/model_backend.py').read_text()
assert any(x in score for x in ['schema":8','schema":9','schema":10'])
for x in ['gesture_profile','gesture_amount','gesture_risk','gesture_anchors']:assert x in score
for x in ['ANCHORS=(0.0,.10,.24,.42,.62,.80,1.0)','bow_speed','micro_pitch_cents','kinetic_response','pizzicato-static']:assert x in graph
for x in ['GESTURE_AMOUNT_OPCODE=122','gesture_windows_v45','smooth_voice_controls_v45','smooth_physical_curves_v45']:assert x in rt
assert 'pe=apply_ensemble_event_timing_v44(pe,sr)' in npb and 'smooth_voice_controls_v45' in npb and 'smooth_voice_controls_v45' in tb
assert 'kParamVoiceGestureAmountBase = 720' in ids and 'kParamVoiceMicroPitchBase = 740' in ids
assert 'gestureAmount=0.f' in ph and 'bend=.50f' in ph
for x in ['decodeGestureVoiceParam','kGestureAmount','kParamVoiceMicroPitchBase:o.bend=v','add(q(o.gestureAmount,4095))']:assert x in proc
for cc in [38,39]:assert f'case {cc}:' in ctl
assert 'String Voice 16 Gesture Amount CC38' in ctl and 'String Voice 16 Micro Pitch CC39' in ctl
assert 'gesture_json' in comp and 'micro_pitch_norm_from_cents' in comp and '38,_cc(n.gesture_amount*127.0)' in comp and '39,micro' in comp
assert 'constexpr int kStateVersion = 13;' in proc and '(version<3||version>13)' in ctl
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)];seen={}
for n,v in pairs:assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
print('SONICRAFT v4.5 Continuous String Gesture source contract OK')
