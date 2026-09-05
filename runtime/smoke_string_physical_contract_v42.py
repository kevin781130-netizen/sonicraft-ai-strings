from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ph=(ROOT/'src/string_physical_v42.h').read_text(encoding='utf-8')
planner=(ROOT/'runtime/string_physical_graph_v42.py').read_text(encoding='utf-8')
runtime=(ROOT/'runtime/string_physical_runtime_v42.py').read_text(encoding='utf-8')
compiler=(ROOT/'runtime/compile_musicxml_strings_v42.py').read_text(encoding='utf-8')
npb=(ROOT/'runtime/control_builder_np.py').read_text(encoding='utf-8')
tb=(ROOT/'runtime/model_backend.py').read_text(encoding='utf-8')

for token in [
 'kParamVoiceStringBase = 520','kParamVoicePositionBase = 540','kParamVoiceBowDirectionBase = 560',
 'kParamVoiceBowChangeBase = 580','kParamVoiceBowPressureBase = 600','kParamVoiceContactPointBase = 620',
 'kParamVoicePortamentoBase = 640','kParamVoiceDeskBase = 660'
]: assert token in ids,token

for cc in [27,28,29,30,31,33,34,35]:
    assert f'case {cc}:' in ctl,cc
for token in ['decodePhysicalVoiceParam','applyStringPhysicalResidualsV42','kPhysString','kPhysDesk']:
    assert token in proc or token in ph,token

# Physical layer is opt-in for backward compatibility.
assert 'if not recognized:' in runtime and 'return None' in runtime
assert ('return o.physicalMask ? applyStringPhysicalResidualsV42' in proc or 'if(o.physicalMask)c=applyStringPhysicalResidualsV42' in proc)
assert 'if phys is not None:' in npb and 'if phys is not None:' in tb

# Judge identity includes per-lane expression + physical state.
assert ('add(o.mask);add(o.physicalMask);' in proc or 'add(o.mask);add(o.physicalMask);add(o.ensembleMask);' in proc)
for token in ['o.physical.stringIndex','o.physical.position','o.physical.bowPressure','o.physical.contactPoint','o.physical.portamento','o.physical.desk']:
    assert token in proc,token

for token in ['OPEN_STRINGS','choose_fingering_path','plan_bowing','plan_portamento','open_string','divisi_desk']:
    assert token in planner,token
for token in ['PHYS_CC','plan_string_physics','physical_notes','acoustic_claim']:
    assert token in compiler,token

# Physical CC choices intentionally skip CC32 (Bank Select LSB).
assert '32:' not in compiler
# State schema does not change: note-level physical data lives in MIDI / Score Graph.
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl

pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n)
    seen[v]=n
print('SONICRAFT v4.2 String Physical Performance source contract OK')
