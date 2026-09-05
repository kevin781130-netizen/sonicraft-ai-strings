from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
pred=(ROOT/'runtime/candidate_utility_predictor_v55.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v55.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v55.py').read_text()
ids=(ROOT/'src/ids.h').read_text();proc=(ROOT/'src/processor.cpp').read_text();ctl=(ROOT/'src/controller.cpp').read_text();cm=(ROOT/'CMakeLists.txt').read_text()
for token in ['CandidateUtilityMemoryV55','predict_candidate_utility_v55','should_escalate_v55','HIGH_CONF=.72','MED_CONF=.48','HIGH_PRED_MARGIN=.12','D Original is always rendered','Skipped slots are intentionally untouched','actual_render_only']:
    assert token in pred,token
assert 'initial=[non_d[0],"D"]' in pred
assert 'initial=[non_d[0],non_d[1],"D"]' in pred
assert 'if float(margin)<MIN_AUDIO_MARGIN' in pred
assert 'predictor_audio_disagreement' in pred
for token in ['"candidate_utility_predictor"','"actual_render_only_learning":True','"D_always_rendered":True','"zero_render_pruning":True']:
    assert token in comp,token
for token in ['CandidateUtilityMemoryV55','predict_candidate_utility_v55','should_escalate_v55','candidate_utility.json','candidate_renders_skipped','candidate_renders_escalated','if escalate and deferred','utility_mem.learn_rendered']:
    assert token in loop,token
assert loop.index('predict_candidate_utility_v55(') < loop.index('render_midi_window_v51(')
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)];seen={}
for n,v in pairs: assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc and '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0']) and 'SonicraftCandidateUtilitySmokeV55' in cm
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1','installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['candidate_utility_predictor_v55.py','compile_musicxml_strings_v55.py','auto_loop_strings_v55.py']: assert token in text,(rel,token)
print('SONICRAFT v5.5 Candidate Utility source contract OK')
