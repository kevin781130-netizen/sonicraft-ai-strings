from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
score=(ROOT/'runtime/score_expression_graph_v40.py').read_text(encoding='utf-8')
solver=(ROOT/'runtime/string_constraint_solver_v43.py').read_text(encoding='utf-8')
compiler=(ROOT/'runtime/compile_musicxml_strings_v43.py').read_text(encoding='utf-8')
cmake=(ROOT/'CMakeLists.txt').read_text(encoding='utf-8')
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
native=(ROOT/'src/string_constraint_v43.h').read_text(encoding='utf-8')

assert any(x in score for x in ['schema":6','schema":7','schema":8','schema":9','schema":10'])
for field in ['constraint_flags','transition_risk','bow_budget','playability_risk',
              'multi_stop_group_id','multi_stop_feasible','divisi_required']:
    assert field in score,field

for token in [
    'solve_string_constraints','_repair_lane','_bow_budget_lane','_assignment_for_multistop',
    'voice_density_exceeds_4x4_bus','configured_range_violation','bow_budget_forced_change',
    'double_stop_consolidated','performance_mode'
]:
    assert token in solver,token

# Stop feasibility must require contiguous strings, not just different strings.
assert 'if any((b-a)!=1 for a,b in zip(strings,strings[1:])):return' in solver
assert 'std::abs(stringA-stringB)!=1' in native

# Solver must actually mutate feasible double-stop fingering/desk state.
for token in ['n.string_index=s','n.finger_semitone=finger','n.divisi_desk=shared_desk']:
    assert token in solver,token

for token in ['constraints_json','_marker','issue.severity.upper()','transition_risk','constraint_solver','constraints.json']:
    assert token in compiler,token

# v4.3 deliberately reuses the v4.2 physical bus: no ParamID expansion.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
assert max(v for _,v in pairs) in (660,700,740), max(v for _,v in pairs)
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n)
    seen[v]=n
assert 'kParamVoiceDeskBase = 660' in ids

# Project state remains v13; the future-aware solver writes MIDI/JSON, not hidden state.
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl

assert any(x in cmake for x in ['VERSION 4.3.0','VERSION 4.4.0','VERSION 4.5.0','VERSION 4.6.0','VERSION 4.7.0','VERSION 4.8.0','VERSION 4.9.0','VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftStringConstraintSmokeV43' in cmake

# Installer/prebuilt paths must include solver/compiler and v4.3 drag/drop entrypoint.
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(encoding='utf-8',errors='ignore')
    for token in ['string_constraint_solver_v43.py','compile_musicxml_strings_v43.py']:
        assert token in text,(rel,token)
assert 'COMPILE_MUSICXML_STRINGS_v43.bat' in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text(encoding='utf-8')
assert 'Tools/COMPILE_MUSICXML_STRINGS_v43.bat' in (ROOT/'installer/tools/verify_prebuilt_layout.py').read_text(encoding='utf-8')

print('SONICRAFT v4.3 String Constraint & Transition source contract OK')
