from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
steer=(ROOT/'runtime/conductor_candidate_steering_v54.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v54.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v54.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'PROFILES=','PRIMARY_SLOTS=','intro','build','sustain','climax','release','resolution',
    'render_slots_for_window_v54','steer_candidate_v54','steer_candidates_v54',
    'D Original is never modified','dynamic_ceiling','Never force vibrato',
    'IMMUTABLE=','base_art','stack','phrase_bow_reserve',
]:
    assert token in steer,token

# Progressive budget must defer exactly the intended low-value candidate.
assert '"climax":("B","C","D")' in steer
assert '"resolution":("A","B","D")' in steer
assert '"release":("A","B","D")' in steer
assert '"intro":("A","B","D")' in steer
assert '"build":("A","B","C","D")' in steer

# Compiler must build intent before repairs, then steer A/B/C before MIDI write.
assert comp.index('conductor_intent=build_conductor_intent_v53(g)') < comp.index('score,issues,candidates,reports,recommended_pre_steer=generate_repairs_v48')
assert comp.index('candidates,steering_report=steer_candidates_v54') < comp.index('write_midi_v47(g,constraints,ensemble,links,out)')
for token in [
    'candidate_steering.json','steered_scores','recommended_pre_steer',
    '"conductor_steered_generation"','"progressive_candidate_budget":True',
    '"deferred_candidate_escalation":True','"D_original_never_steered":True'
]:
    assert token in comp,token

# Auto-loop must render primary set first and only escalate deferred candidates on low margin.
for token in [
    'render_slots_for_window_v54','active=list(budget["active"])','deferred=list(budget["deferred"])',
    'if margin<MIN_MARGIN and deferred','candidate_renders_escalated+=1',
    'candidate_renders_skipped+=len(deferred)','"candidate_budget"',
    '"initial_margin"','"final_margin"'
]:
    assert token in loop,token

# Downstream guards remain present.
for token in [
    'choose_conductor_locked_decisions_v53','global_pair_verify_failed',
    'splice_midi_windows_v51','D_GLOBAL_VERIFY.wav'
]:
    assert token in loop,token

# No realtime state/control surface expansion.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftConductorSteeringSmokeV54' in cm

for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['conductor_candidate_steering_v54.py','compile_musicxml_strings_v54.py','auto_loop_strings_v54.py']:
        assert token in text,(rel,token)
collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v54.bat','AUTO_LOOP_STRINGS_v54.bat']:
    assert token in collector,token
assert 'Tools/COMPILE_MUSICXML_STRINGS_v54.bat' in verify
assert 'Tools/AUTO_LOOP_STRINGS_v54.bat' in verify

print('SONICRAFT v5.4 Conductor-Steered Candidate source contract OK')
