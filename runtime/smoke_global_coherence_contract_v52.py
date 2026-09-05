from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
guard=(ROOT/'runtime/global_performance_coherence_v52.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v52.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v52.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'dynamic_trajectory','vibrato_character','bow_energy','desk_looseness',
    'transition_density','section_role','PASS_SCORE=82.0','MAX_EDGE_EXCESS=1.45',
    'AUDIO_DROP_LIMIT=.075','choose_coherent_decisions_v52',
    'merge_graph_decisions_v52','_decision_selects_note',
    'phrase:{pid}','coherence_override','no_coherent_candidate_combination',
]:
    assert token in guard,token

# Candidate search must retain D as an explicit safety option.
assert 'if "D" in scores' in guard
assert 'allowed.append("D")' in guard
assert 'product(*allowed)' in guard

# Auto-loop must run guard before MIDI merge and pair verify after full merged render.
for token in [
    'choose_coherent_decisions_v52','global_coherence.json',
    'coherent_decisions is None','full_fallback_global_coherence',
    'splice_midi_windows_v51','D_GLOBAL_VERIFY.wav',
    'pair_delta>=-.025','pair_safety_delta>=-.04',
    'global_pair_verify_failed','full_fallback_pair_verify',
]:
    assert token in loop,token
assert loop.index('choose_coherent_decisions_v52(') < loop.index('splice_midi_windows_v51(')

# v5.2 compiler exposes candidate graphs and advertises the guard.
for token in [
    '"version":"5.2"','"global_coherence_guard"','"pass_score":82.0',
    '"max_edge_excess":1.45','"candidate_substitution_search":True',
    '"full_pair_verify":True','"candidate_graphs":candidates',
    'AUTO_LOOP_STRINGS_v52.bat'
]:
    assert token in comp,token

# Realtime state/control surface remains unchanged.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n)
    seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftGlobalCoherenceSmokeV52' in cm

# Installer/prebuilt must carry v5.2 runtime + entrypoints.
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['global_performance_coherence_v52.py','compile_musicxml_strings_v52.py','auto_loop_strings_v52.py']:
        assert token in text,(rel,token)

collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v52.bat','AUTO_LOOP_STRINGS_v52.bat']:
    assert token in collector,token
assert 'Tools/COMPILE_MUSICXML_STRINGS_v52.bat' in verify
assert 'Tools/AUTO_LOOP_STRINGS_v52.bat' in verify

print('SONICRAFT v5.2 Global Performance Coherence source contract OK')
