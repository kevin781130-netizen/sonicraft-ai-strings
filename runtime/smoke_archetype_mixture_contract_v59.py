from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
mix=(ROOT/'runtime/archetype_mixture_v59.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v59.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v59.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'SOFTMAX_TEMP=.105','MAX_COMPONENTS=3','MIN_COMPONENT_WEIGHT=.08',
    'MIXTURE_CONF_FLOOR=.42','MIXTURE_CONF_CAP_NO_LOCAL=.66',
    'mixture_from_distances_v59','soft_classify_archetype_v59',
    'ArchetypeMixtureMemoryV59','collect_mixture_evidence_v59',
    'learn_mixture_rendered_v59','predict_candidate_utility_v59',
    'component-to-context aggregate calibration only',
    'mixture-only evidence can at most unlock Top2+D',
]:
    assert token in mix,token

# Soft weights and safety gate.
assert 'math.exp(-(float(distances[k])-d0)/SOFTMAX_TEMP)' in mix
assert 'if float(base.local_evidence)<.5 and float(base.transfer_evidence)<.5:' in mix
assert 'confidence=min(confidence,MIXTURE_CONF_CAP_NO_LOCAL)' in mix
assert 'float(base.local_evidence)>=HIGH_LOCAL_EVIDENCE_FLOOR' in mix

# Compile from D-derived Conductor Intent before candidate generation.
body=comp[comp.index('def compile_file'):]
assert body.index('conductor_intent=build_conductor_intent_v53(g)') < body.index('archetype_mixture=soft_classify_archetype_v59(conductor_intent)')
assert body.index('archetype_mixture=soft_classify_archetype_v59(conductor_intent)') < body.index('generate_repairs_v48')
for token in [
    'performance_archetype_mixture.json','"performance_archetype_mixture"',
    '"soft_archetype_mixture"','"mixture_only_top1_forbidden":True',
    '"component_edge_audit_calibration":True','"mixture_json":mixture_json',
]:
    assert token in comp,token

# Auto-loop must use v5.9 mixture predictor, weighted rendered-only learning and isolated audit.
for token in [
    'ArchetypeMixtureMemoryV59','predict_candidate_utility_v59',
    'learn_mixture_rendered_v59','mixture_memory_path',
    'prediction.mixture_evidence>0','mixture_mem.record_audit',
    'archetype_mixture_memory.json','archetype_mixture_audit_events',
    '"v58_archetype_trust_not_mutated":True','"v57_transfer_edges_not_mutated":True',
]:
    assert token in loop,token
assert 'transfer_mem.record_audit' in loop
assert 'archetype_mem.record_audit' not in loop  # v5.9 failures must not mutate v5.8 hard-archetype trust.

# No realtime control/state expansion.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftArchetypeMixtureSmokeV59' in cm

# Installer / prebuilt.
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['archetype_mixture_v59.py','compile_musicxml_strings_v59.py','auto_loop_strings_v59.py']:
        assert token in text,(rel,token)
collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v59.bat','AUTO_LOOP_STRINGS_v59.bat']:
    assert token in collector,token
assert 'Tools/COMPILE_MUSICXML_STRINGS_v59.bat' in verify
assert 'Tools/AUTO_LOOP_STRINGS_v59.bat' in verify

print('SONICRAFT v5.9 Soft Archetype Mixture source contract OK')
