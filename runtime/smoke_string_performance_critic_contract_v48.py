from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
critic=(ROOT/'runtime/string_performance_critic_v48.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v48.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'WEIGHTS','bow_reserve','transition','vibrato','dynamics_arc','gesture_spikes','ensemble_alignment',
    'repair_candidate_v48','generate_repairs_v48','Conservative','Balanced','Expressive',
    'structural_recommendation','final_authority'
]:
    assert token in critic,token

# A/B/C must be materially differentiated in code, not aliases.
assert '"A":{"blend":.24' in critic
assert '"B":{"blend":.52' in critic and '"rebow":True' in critic
assert '"C":{"blend":.36' in critic and '"expressive":True' in critic
assert 'safe_rebow_split' in critic
assert 'deepcopy(g)' in critic

for token in [
    'midi_A','midi_B','midi_C','midi_D','critic_json','judge_queue_json',
    'A Conservative','B Balanced','C Expressive','D Original',
    'audio_judge_required_for_final_winner','existing SONICRAFT Audio Judge'
]:
    assert token in comp,token

assert 'write_midi_v47(g,constraints,ensemble,links,out)' in comp
assert 'write_midi_v47(candidates[slot],constraints,ensemble,links,cp)' in comp
assert 'b.replace(b"v4.7",b"v4.8")' in comp

# v4.8 adds no new automation/control family.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n)
    seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl

assert any(x in cm for x in ['VERSION 4.8.0','VERSION 4.9.0','VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftStringPerformanceCriticSmokeV48' in cm

for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['string_performance_critic_v48.py','compile_musicxml_strings_v48.py']:
        assert token in text,(rel,token)
assert 'COMPILE_MUSICXML_STRINGS_v48.bat' in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
assert 'Tools/COMPILE_MUSICXML_STRINGS_v48.bat' in (ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
print('SONICRAFT v4.8 Performance Critic & Auto-Repair source contract OK')
