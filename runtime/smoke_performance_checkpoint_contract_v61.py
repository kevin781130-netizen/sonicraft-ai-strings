from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
cp=(ROOT/'runtime/performance_checkpoint_v61.py').read_text()
store=(ROOT/'runtime/evidence_store_v60.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v61.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v61.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'CHECKPOINT_SCHEMA=1','CHECKPOINT_VERSION="6.1"',
    'CODE_FILES=','ARTIFACT_KEYS=',
    '"midi_D","midi_A","midi_B","midi_C"',
    'source":{"sha256"','compiler":code_fingerprint_v61',
    '"evidence":evidence','"repair_policy":policy',
    '"conductor_intent_hash"','"candidate_steering_intent_hash"',
    'create_compile_checkpoint_v61','finalize_checkpoint_v61',
    'verify_checkpoint_v61','replay_verify_checkpoint_v61',
    'restore_checkpoint_environment_v61','release_checkpoint_pin_v61',
    '"audio_embedded":False','"midi_embedded":False',
    '"exact_audio_replay_claimed":False',
]:
    assert token in cp,token

# JSON normalization must ignore only machine-path fields; MIDI remains raw hash.
for token in ['"source_score","queue_dir","policy_path","persistent_policy_path"',
              '"normalized_sha256"','"raw_sha256"','_sha_bytes(raw)']:
    assert token in cp,token
assert '"expected_render"' not in re.search(r'VOLATILE_JSON_KEYS=\{(.*?)\}',cp,re.S).group(1)
assert 'def _checkpoint_identity_projection_v61' in cp
assert 'row.pop("raw_sha256",None)' in cp
assert 'row.pop("bytes",None)' in cp
assert 'q["source"].pop("file_name",None)' in cp
assert 'checkpoint_result_binding_mismatch' in cp

# Replay is non-destructive: temporary policy + compile, no evidence rollback call.
replay=cp[cp.index('def replay_verify_checkpoint_v61'):cp.index('def restore_checkpoint_environment_v61')]
assert 'TemporaryDirectory' in replay
assert '_write_policy_payload(policy' in replay
assert 'compile_file(' in replay
assert '.rollback(' not in replay
assert 'restore_commit' not in replay

# Restore explicitly moves evidence + policy and backs policy up.
restore=cp[cp.index('def restore_checkpoint_environment_v61'):cp.index('def release_checkpoint_pin_v61')]
assert 'backup_policy' in restore
assert '.pre_v61_restore.bak' in restore
assert 'evidence_store.rollback' in restore
assert '_write_policy_payload' in restore

# Evidence Store pinning is part of v6.1 long-term retention.
for token in ['self.pins={}','def pin_commit','def unpin_commit','def pinned_commits',
              'set(self.pinned_commits())','"pinned_commits":len(self.pinned_commits())']:
    assert token in store,token
create=cp[cp.index('def create_compile_checkpoint_v61'):cp.index('def _policy_snapshot_from_file')]
assert 'evidence_store.pin_commit' in create
assert '"@CHECKPOINT_PIN@"' in cp
release=cp[cp.index('def release_checkpoint_pin_v61'):cp.index('def _paths_from_args')]
assert 'evidence_store.unpin_commit' in release

# Auto-loop creates checkpoint immediately after compile and before local evidence consumption.
body=loop[loop.index('def run_auto_loop_v61'):]
compile_i=body.index('comp=compile_file(')
checkpoint_i=body.index('create_compile_checkpoint_v61(',compile_i)
predict_i=body.index('predict_candidate_utility_v59(',checkpoint_i)
assert compile_i<checkpoint_i<predict_i
assert 'finalize_checkpoint_v61(' in body
assert '"performance_checkpoint":str(checkpoint_path)' in body
assert '"checkpoint_result_binding"' in body

# Compiler advertises checkpoint contract.
for token in ['"reproducible_performance_checkpoint"','"non_destructive_replay_verify":True',
              '"explicit_environment_restore":True','"audio_embedded":False',
              'AUTO_LOOP_STRINGS_v61.bat']:
    assert token in comp,token

# Management entrypoint ships verify/replay/restore/release.
bat=(ROOT/'PERFORMANCE_CHECKPOINT_V61.bat').read_text(errors='ignore')
for token in ['verify','replay','restore','release','performance_checkpoint_v61.py']:
    assert token in bat,token

# No realtime/state expansion.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert 'VERSION 6.1.0' in cm
assert 'SonicraftPerformanceCheckpointSmokeV61' in cm

# Installer/prebuilt.
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['performance_checkpoint_v61.py','compile_musicxml_strings_v61.py','auto_loop_strings_v61.py']:
        assert token in text,(rel,token)
collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v61.bat','AUTO_LOOP_STRINGS_v61.bat','PERFORMANCE_CHECKPOINT_V61.bat']:
    assert token in collector,token
for token in ['Tools/COMPILE_MUSICXML_STRINGS_v61.bat','Tools/AUTO_LOOP_STRINGS_v61.bat','Tools/PERFORMANCE_CHECKPOINT_V61.bat']:
    assert token in verify,token

print('SONICRAFT v6.1 Reproducible Performance Checkpoint source contract OK')
