from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
store=(ROOT/'runtime/evidence_store_v60.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v60.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v60.py').read_text()
ids=(ROOT/'src/ids.h').read_text()
proc=(ROOT/'src/processor.cpp').read_text()
ctl=(ROOT/'src/controller.cpp').read_text()
cm=(ROOT/'CMakeLists.txt').read_text()

# Five namespaces remain separate; governance is unified.
for token in [
    'NAMESPACES=("utility_v55","audit_v56","similarity_v57","archetype_v58","mixture_v59")',
    'STORE_VERSION=1','MAX_COMMITS=32','MAX_NAMESPACE_BYTES=2*1024*1024',
    'class UnifiedEvidenceStoreV60','commit_payloads','capture_legacy',
    'bootstrap_or_recover','quarantine_bytes','restore_commit','rollback',
    'compact','export_bundle','import_bundle','verify_legacy',
    'zlib.compress','hashlib.sha256','content-addressed',
]:
    assert token in store,token

# Privacy/contamination contract is structural, recursive, and excludes work identity/content.
for token in ['FORBIDDEN_STRUCTURAL_KEYS','_walk_bad_keys','forbidden_structural_field',
              '"audio"','"midi"','"score_text"','"song_title"','"note_sequence"','"intent_hash"','"user_id"']:
    assert token in store,token

# v4.9 Repair Policy is intentionally not one of the evidence namespaces.
assert 'repair_policy_v49' not in re.search(r'NAMESPACES=\((.*?)\)',store,re.S).group(1)

# Auto-loop MUST recover before legacy memory objects are instantiated.
body=loop[loop.index('def run_auto_loop_v60'):]
recover=body.index('evidence_store.bootstrap_or_recover(evidence_paths)')
for token in [
    'CandidateUtilityMemoryV55(utility_path)',
    'CounterfactualAuditMemoryV56(audit_path_mem)',
    'SimilarityTransferMemoryV57(transfer_path_mem)',
    'PerformanceArchetypeMemoryV58(archetype_path_mem)',
    'ArchetypeMixtureMemoryV59(mixture_path_mem)',
]:
    assert recover < body.index(token),(recover,token)

# All five local-memory writes are transactionally captured before low-confidence/full-fallback branch.
commit=body.index('evidence_store.capture_legacy(')
low=body.index('if low_conf:',commit)
assert commit<low
assert 'evidence_store.verify_legacy(evidence_paths)' in body[commit:low+500]
assert 'evidence_store_post_commit_verification_failed' in body

# Compiler advertises store capability without changing musical compile path.
for token in ['"unified_evidence_store"','"atomic_multi_namespace_commit":True',
              '"rollback":True','"quarantine":True','"export_import":True',
              '"legacy_json_compatible":True','AUTO_LOOP_STRINGS_v60.bat']:
    assert token in comp,token

# Management entrypoint exists.
assert (ROOT/'EVIDENCE_STORE_V60.bat').is_file()
bat=(ROOT/'EVIDENCE_STORE_V60.bat').read_text(errors='ignore')
for token in ['status','verify','compact','export','rollback','evidence_store_v60.py']:
    assert token in bat,token

# Realtime/state surface unchanged.
pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftEvidenceStoreSmokeV60' in cm

# Installer/prebuilt ships runtime + management tool.
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['evidence_store_v60.py','compile_musicxml_strings_v60.py','auto_loop_strings_v60.py']:
        assert token in text,(rel,token)
collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v60.bat','AUTO_LOOP_STRINGS_v60.bat','EVIDENCE_STORE_V60.bat']:
    assert token in collector,token
for token in ['Tools/COMPILE_MUSICXML_STRINGS_v60.bat','Tools/AUTO_LOOP_STRINGS_v60.bat','Tools/EVIDENCE_STORE_V60.bat']:
    assert token in verify,token

print('SONICRAFT v6.0 Unified Evidence Store source contract OK')
