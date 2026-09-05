from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ph=(ROOT/'src/processor.h').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ui=(ROOT/'resource/SONICRAFT_AI_Strings_Q4.uidesc').read_text(encoding='utf-8')
shadow=(ROOT/'src/shadow_render_client.cpp').read_text(encoding='utf-8')
pref=(ROOT/'src/preference_client_v38.cpp').read_text(encoding='utf-8')
protocol=(ROOT/'runtime/protocol.py').read_text(encoding='utf-8')
service=(ROOT/'runtime/renderer_service.py').read_text(encoding='utf-8')
memory=(ROOT/'runtime/judge_memory_v38.py').read_text(encoding='utf-8')
gate=(ROOT/'src/preference_auto_comp_v39.h').read_text(encoding='utf-8')
cmake=(ROOT/'CMakeLists.txt').read_text(encoding='utf-8')
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
for x in ['kParamPersonalTasteEnable = 340','kParamPersonalTasteStrength = 341','kParamPersonalTasteLearn = 342','kParamPersonalTasteClear = 343','kParamPersonalConfidence = 344','kParamPersonalWeightBase = 346','kParamPersonalScoreBase = 351','kParamPreferenceAutoComp = 355','kParamPreferenceAutoCompReview = 363']:
    assert x in ids,x
# Part automation remains below 334; personalization starts at 340.
assert 'kParamPartSpeedProfileBase = 330' in ids
# Wire compatibility and local profile protocol.
assert "JUDGE_RESULT = struct.Struct('<HBB24f')" in protocol
assert "JUDGE_RESULT_V2 = struct.Struct('<HBB34fI')" in protocol
assert 'JUDGE_CAP_PERSONAL = 0x8000' in protocol and 'TYPE_PREFERENCE = 4' in protocol and 'TYPE_PROFILE_QUERY = 5' in protocol and 'TYPE_PROFILE_CLEAR = 6' in protocol
assert 'personal_cap=' in service and 'self.judge_memory.personalize' in service
# Safety / bounded / confidence invariants.
assert 'self.weights[4]=max(0.0' in memory
assert '*0.12*snap.confidence*strength' in memory
assert 'feat[:,4]<0.20' in memory
assert '1.0-math.exp(-max(0.0,float(evidence))/13.0)' in memory
# Audio thread only queues preference events; networking/JSON are worker/service side.
assert 'ring.push(e);' in pref and 'workerMain' in pref
assert 'PreferenceClientV38 preference;' in ph
assert 'oldFav' in proc and 'oldRej' in proc and 'tokenMatch' in proc
# stale profile protection is applied before UI/commit and auto comp.
assert 'judgeMatchesCurrentProfile' in proc
assert 'snap.profileHash32==uint32_t(profile.hash&0xFFFFFFFFu)' in proc
# v3.9 sequential async queue + one final batch commit; auto commit is not fed back as preference evidence.
assert 'preferenceAutoCompWaiting' in proc
assert 'evaluatePreferenceAutoCompV39' in proc
assert 'phraseTakeComp.commitBatch(preferenceCandidateKeys,preferenceCandidateTakes,preferenceCandidateCount)' in proc
batch=proc[proc.index('// v3.9: one async Audio Judge'):proc.index('shadow.mix(',proc.index('// v3.9: one async Audio Judge'))]
assert 'preference.record' not in batch
assert 'profileConfidence>=minConfidence' in gate and 'd.margin>=minMargin' in gate and 'd.safety>=safetyFloor' in gate
# State order: v13 settings are written before the comp payload and controller reads them before compCount.
w=proc.index('s.writeFloat(personalTasteEnable)'); compw=proc.index('const int compCount=phraseTakeComp.exportEntries'); assert w<compw
state=ctl[ctl.index('setComponentState'):]; r=state.index('float p13[6]'); compr=state.index('s.readInt32(compCount)'); assert r<compr
# Installer blocker regression: both runtime modules are mandatory in all four release paths.
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1','installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    s=(ROOT/rel).read_text(encoding='utf-8')
    assert 'audio_take_judge_v37.py' in s and 'judge_memory_v38.py' in s,rel
assert 'src/preference_client_v38.cpp' in cmake and any(v in cmake for v in ['VERSION 3.9.0','VERSION 4.1.0','VERSION 4.2.0','VERSION 4.3.0','VERSION 4.4.0','VERSION 4.5.0','VERSION 4.6.0','VERSION 4.7.0','VERSION 4.8.0','VERSION 4.9.0','VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
# Expanded UI fits current constraints.
assert 'size="1120,1210" minSize="900,1000" maxSize="1500,1400"' in ui
assert 'VSTGUI::CPoint(900, 1000), VSTGUI::CPoint(1500, 1400)' in ctl
# Explicit numeric IDs must be unique (base ranges are intentionally disjoint as above).
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n)
    seen[v]=n
print('SONICRAFT v3.9 Preference-Guided Auto Comp source contract OK')
