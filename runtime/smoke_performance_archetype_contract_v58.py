from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
arch=(ROOT/'runtime/performance_archetype_memory_v58.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v58.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v58.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'PROTOTYPES=','intimate','ballad','dramatic','chamber','cinematic',
    'classify_archetype_v58','PerformanceArchetypeMemoryV58',
    'predict_candidate_utility_v58','ARCHETYPE_CONF_FLOOR=.42',
    'ARCHETYPE_CONF_CAP_NO_LOCAL=.66','Cross-song archetype evidence cannot by itself cause Top1+D',
    'actual_render_only','no audio/MIDI/score text/file names/note sequences/intent hashes',
]:
    assert token in arch,token

# Persistent memory must not store work identity.
for forbidden_field in ['"song_title":','"filename":','"note_sequence":','"intent_hash":']:
    assert forbidden_field not in arch,forbidden_field

# Compiler derives archetype from D Original before candidate render and writes a project sidecar.
body=comp[comp.index('def compile_file'):]
assert body.index('conductor_intent=build_conductor_intent_v53(g)') < body.index('archetype=classify_archetype_v58(conductor_intent)')
assert body.index('archetype=classify_archetype_v58(conductor_intent)') < body.index('generate_repairs_v48')
for token in [
    'performance_archetype.json','"performance_archetype"','"cross_song_archetype_memory"',
    '"archetype_only_top1_forbidden":True','"control_profile_only":True',
    '"audit_calibrated":True','"archetype":archetype'
]:
    assert token in comp,token

# Auto-loop combines v5.7 with archetype prior and isolates audit calibration.
for token in [
    'PerformanceArchetypeMemoryV58','predict_candidate_utility_v58',
    'archetype_memory_path','archetype_mem.learn_rendered',
    'prediction.archetype_evidence>0','archetype_mem.record_audit',
    'performance_archetype_memory.json','performance_archetype_audit_events',
    '"archetype_only_top1_forbidden":True','actual_render_only_learning'
]:
    assert token in loop,token
# Similarity transfer and archetype audit are independent calls.
assert 'transfer_mem.record_audit' in loop
assert 'archetype_mem.record_audit' in loop

# No realtime surface expansion.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftPerformanceArchetypeSmokeV58' in cm

for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['performance_archetype_memory_v58.py','compile_musicxml_strings_v58.py','auto_loop_strings_v58.py']:
        assert token in text,(rel,token)

collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v58.bat','AUTO_LOOP_STRINGS_v58.bat']:
    assert token in collector,token
assert 'Tools/COMPILE_MUSICXML_STRINGS_v58.bat' in verify
assert 'Tools/AUTO_LOOP_STRINGS_v58.bat' in verify

print('SONICRAFT v5.8 Cross-Song Performance Archetype source contract OK')
