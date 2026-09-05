from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
cp=(ROOT/'runtime/performance_checkpoint_v62.py').read_text()
prov=(ROOT/'runtime/acoustic_runtime_provenance_v62.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v62.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v62.py').read_text()
ids=(ROOT/'src/ids.h').read_text(); proc=(ROOT/'src/processor.cpp').read_text(); ctl=(ROOT/'src/controller.cpp').read_text(); cm=(ROOT/'CMakeLists.txt').read_text()
for token in ['CHECKPOINT_SCHEMA=1','CHECKPOINT_VERSION="6.2"','"acoustic_runtime":acoustic_runtime','"acoustic_runtime_bound":True','"acoustic_environment_explainable":True','"exact_audio_replay_claimed":False','verify_acoustic_runtime_provenance_v62','export_in_toto_slsa_envelope_v62']:
    assert token in cp,token
for token in ['PROVENANCE_SCHEMA = 1','PROVENANCE_VERSION = "6.2"','release_model_manifest.json','actual_sha256','hash_match','get_device_capability','get_available_providers','get_build_info','nvidia-smi','render_config','binding_sha256','https://in-toto.io/Statement/v1','https://slsa.dev/provenance/v1']:
    assert token in prov,token
assert 'if isinstance(ar,dict): ar.pop("forensics",None)' in cp
assert 'create_compile_checkpoint_v62(' in loop
assert 'capture_acoustic_runtime_provenance_v62(' in loop
assert loop.index('capture_acoustic_runtime_provenance_v62(') < loop.index('create_compile_checkpoint_v62(')
for token in ['"acoustic_runtime_provenance":True','"model_weight_sha256"','"device_capability"','AUTO_LOOP_STRINGS_v62.bat']:
    assert token in comp,token
bat=(ROOT/'PERFORMANCE_CHECKPOINT_V62.bat').read_text(errors='ignore')
for token in ['verify','replay','restore','release','provenance','performance_checkpoint_v62.py']: assert token in bat,token
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]; seen={}
for n,v in pairs: assert v not in seen,(v,seen.get(v),n); seen[v]=n
assert any(n=='kParamVoiceMicroPitchBase' and v==740 for n,v in pairs)
# v6.4 adds non-MIDI frontend/mixer parameters outside the frozen voice-control ranges.
assert max(v for _,v in pairs) in (740,828)
assert any(x in proc for x in ['constexpr int kStateVersion = 13;','constexpr int kStateVersion = 14;'])
assert any(x in ctl for x in ['(version<3||version>13)','(version<3||version>14)'])
assert any(x in cm for x in ['VERSION 6.2.0','VERSION 6.4.0']) and 'SonicraftPerformanceCheckpointSmokeV62' in cm
print('SONICRAFT v6.2 Acoustic Runtime Provenance source contract OK')
