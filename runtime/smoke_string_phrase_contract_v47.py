from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
score=(ROOT/'runtime/score_expression_graph_v40.py').read_text()
graph=(ROOT/'runtime/string_phrase_longline_v47.py').read_text()
runtime=(ROOT/'runtime/string_phrase_runtime_v47.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v47.py').read_text()
npb=(ROOT/'runtime/control_builder_np.py').read_text()
tb=(ROOT/'runtime/model_backend.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in ['phrase_longline_id','phrase_bow_reserve','phrase_dynamic_momentum','phrase_vibrato_rate_hz','phrase_longline_flags']:
    assert token in score,token
for token in ['plan_phrase_longlines_v47','PhraseArcV47','phraseEnergy' if False else 'phrase_energy_arc','vibrato_rate_target','SENTINEL_NORM']:
    assert token in graph,token
for token in ['phrase_windows_v47','SENTINEL_MAX','apply_phrase_longline_v47','vibrato_rate_hz' if False else 'rate_hz','depth_cents']:
    assert token in runtime,token
assert 'if not windows:' in runtime
for token in ['plan_phrase_longlines_v47','phrase_json','CC38 1/127 sentinel','phrase_longline']:
    assert token in comp,token
assert 'bytes([0xB0|ch,38,1])' in comp
assert 'apply_phrase_longline_v47' in npb and 'apply_phrase_longline_v47' in tb
assert 'vibrato_depth_cents=vib_depth_cents' in npb
assert 'vibrato_depth_cents=T(vib_depth_cents)' in tb
assert 'vibrato_rate_hz=T(vib_rate_hz)' in tb

# No new automation family in v4.7.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert any(x in cm for x in ['VERSION 4.7.0','VERSION 4.8.0','VERSION 4.9.0','VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftStringPhraseSmokeV47' in cm
print('SONICRAFT v4.7 Phrase Long-Line source contract OK')
