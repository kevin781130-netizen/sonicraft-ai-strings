from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
intent=(ROOT/'runtime/conductor_intent_v53.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v53.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v53.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'SectionIntentV53','ConductorIntentV53','build_conductor_intent_v53',
    'evaluate_conductor_intent_v53','choose_conductor_locked_decisions_v53',
    'intro','build','sustain','climax','release','resolution',
    'INTENT_PASS_SCORE=84.0','MAX_SECTION_EXCESS=1.55','AUDIO_DROP_LIMIT=.075',
    'climax_shift_','premature_dynamic_ceiling_','long_line_direction_reversal_',
    'part_{p}_{role}_lock_lost','_character_prior',
    'intent_hash','D Original is always a safety candidate'
]:
    assert token in intent,token

# Search must require both v5.2 coherence and v5.3 intent.
assert 'if not coh.passed:continue' in intent
assert 'if not ir.passed:continue' in intent
assert '_allowed_slots(d)' in intent
assert 'merge_graph_decisions_v52' in intent

# Compiler must extract intent only from D graph and write a sidecar.
for token in [
    'build_conductor_intent_v53(g)','conductor_intent.json',
    'conductor_json.write_text','"conductor_intent_lock"',
    '"intent_pass_score":84.0','"max_section_excess":1.55',
    '"long_line_direction_lock":True','"role_lock":True',
    '"dynamic_ceiling_lock":True','"conductor_intent":conductor_intent'
]:
    assert token in comp,token

# Auto-loop must apply conductor lock before selective merge.
for token in [
    'choose_conductor_locked_decisions_v53','conductor_lock.json',
    'locked_decisions is None','full_fallback_conductor_intent',
    'decisions=locked_decisions','splice_midi_windows_v51',
    '"conductor_intent_report"','"conductor_override"',
    'selective_conductor_lock','global_pair_verify_failed'
]:
    assert token in loop,token
assert loop.index('choose_conductor_locked_decisions_v53(') < loop.index('splice_midi_windows_v51(')

# No realtime control/state expansion.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftConductorIntentSmokeV53' in cm

# Installer/prebuilt inclusion.
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['conductor_intent_v53.py','compile_musicxml_strings_v53.py','auto_loop_strings_v53.py']:
        assert token in text,(rel,token)
collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v53.bat','AUTO_LOOP_STRINGS_v53.bat']:
    assert token in collector,token
assert 'Tools/COMPILE_MUSICXML_STRINGS_v53.bat' in verify
assert 'Tools/AUTO_LOOP_STRINGS_v53.bat' in verify

print('SONICRAFT v5.3 Long-Form Conductor Intent source contract OK')
