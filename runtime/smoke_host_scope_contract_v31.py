from pathlib import Path
import re, xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
ids=(root/'src/ids.h').read_text()
proc=(root/'src/processor.cpp').read_text()
ctrl=(root/'src/controller.cpp').read_text()
ui=(root/'resource/SONICRAFT_AI_Strings_Q4.uidesc').read_text()
cm=(root/'CMakeLists.txt').read_text()
expected={'kParamHostScopeMode':120,'kParamHostScopeStyle':121,'kParamHostScopeLooseness':122}
for name,val in expected.items():
    m=re.search(rf'\b{name}\s*=\s*(\d+)',ids); assert m and int(m.group(1))==val,(name,m.group(1) if m else None)
    assert name in proc and name in ctrl
assert 'kNeedCycleMusic' in proc
assert 'cycleStartMusic' in proc and 'cycleEndMusic' in proc and 'projectTimeMusic' in proc
assert 'boundarySampleOffset' in proc and 'resolveHostScope' in proc
m=re.search(r'constexpr int kStateVersion = (\d+);',proc); assert m and int(m.group(1))>=7
m=re.search(r'version>(\d+)',ctrl); assert m and int(m.group(1))>=7
assert 'Host Scope' in ctrl and 'Host Scope Style' in ctrl and 'Host Scope Looseness' in ctrl
ET.parse(root/'resource/SONICRAFT_AI_Strings_Q4.uidesc')
for tag in ('HostScopeMode','HostScopeStyle','HostScopeLooseness'):
    assert f'name="{tag}"' in ui
assert 'SonicraftHostCycleScopeSmokeV31' in cm
# Safety: CC 120..127 are channel-mode messages and must not be assigned as host-command CCs.
h=(root/'src/host_command_lane_v30.h').read_text()
vals=[int(v) for v in re.findall(r'kCC_[A-Za-z0-9_]+\s*=\s*(\d+)',h)]
assert max(vals)==119 and not any(v>=120 for v in vals)
print('SONICRAFT v3.1 host-scope source contract smoke OK')
