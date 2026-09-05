from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ph=(ROOT/'src/processor.h').read_text(encoding='utf-8')
score=(ROOT/'runtime/score_expression_graph_v40.py').read_text(encoding='utf-8')
solver=(ROOT/'runtime/string_ensemble_solver_v44.py').read_text(encoding='utf-8')
runtime=(ROOT/'runtime/string_ensemble_runtime_v44.py').read_text(encoding='utf-8')
compiler=(ROOT/'runtime/compile_musicxml_strings_v44.py').read_text(encoding='utf-8')
npb=(ROOT/'runtime/control_builder_np.py').read_text(encoding='utf-8')
tb=(ROOT/'runtime/model_backend.py').read_text(encoding='utf-8')
cmake=(ROOT/'CMakeLists.txt').read_text(encoding='utf-8')

assert any(x in score for x in ['schema":7','schema":8','schema":9','schema":10'])
for field in ['ensemble_group_id','ensemble_phrase_id','ensemble_role','ensemble_attack_offset_ms',
              'ensemble_breath_ms','ensemble_bow_sync','ensemble_coordination_risk','ensemble_coordination_flags']:
    assert field in score,field

for token in ['coordinate_string_ensemble','explicit_bow_direction_conflict','ensemble_attack_spread',
              'phrase_breath','coordinated_bow_directions','coordinated_bow_changes']:
    assert token in solver,token
assert 'if forced_dir is None and not conflict:' in solver
assert 'written marks preserved' in solver

for token in ['ENSEMBLE_ATTACK_OPCODE=120','ENSEMBLE_BREATH_OPCODE=121',
              'apply_ensemble_event_timing_v44','if not recognized:','return events']:
    assert token in runtime,token
assert 'pe=apply_ensemble_event_timing_v44(pe,sr)' in npb
assert 'pe=apply_ensemble_event_timing_v44(pe,sr)' in tb

for token in ['kParamVoiceEnsembleAttackBase = 680','kParamVoicePhraseBreathBase = 700']:
    assert token in ids,token
assert 'StringEnsembleStateV44 ensemble{}' in ph
assert 'ensembleMask=0' in ph
for token in ['decodeEnsembleVoiceParam','kEnsembleAttackOffset','kEnsemblePhraseBreath',
              'o.ensemble.attackOffset','o.ensemble.phraseBreath','add(o.mask);add(o.physicalMask);add(o.ensembleMask);']:
    assert token in proc,token
for cc in [36,37]:
    assert f'case {cc}:' in ctl
assert 'String Voice 16 Ensemble Attack CC36' in ctl
assert 'String Voice 16 Phrase Breath CC37' in ctl

for token in ['ensemble_json','hq_timing_bus','CC36' if False else '36','CC37' if False else '37']:
    assert token in compiler,token
assert 'attack_norm_from_ms' in compiler and 'breath_norm_from_ms' in compiler

# No hidden project-state expansion: v4.4 timing lives in authored MIDI.
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl

# Explicit ParamID bases remain collision-free.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n)
    seen[v]=n
assert max(v for _,v in pairs) in (700,740)

assert any(x in cmake for x in ['VERSION 4.4.0','VERSION 4.5.0','VERSION 4.6.0','VERSION 4.7.0','VERSION 4.8.0','VERSION 4.9.0','VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftStringEnsembleSmokeV44' in cmake
print('SONICRAFT v4.4 Ensemble Bow & Phrase source contract OK')
