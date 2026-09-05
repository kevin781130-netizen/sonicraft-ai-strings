from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
transfer=(ROOT/'runtime/context_similarity_transfer_v57.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v57.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v57.py').read_text()
ids=(ROOT/'src/ids.h').read_text();proc=(ROOT/'src/processor.cpp').read_text();ctl=(ROOT/'src/controller.cpp').read_text();cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'MIN_JACCARD=.34','TRANSFER_EVIDENCE_SCALE=.32','MAX_TRANSFER_EVIDENCE_PER_SLOT=4.0',
    'TRANSFER_CONF_CAP_NO_LOCAL=.68','HIGH_LOCAL_EVIDENCE_FLOOR=1.5',
    'context_similarity_v57','collect_transfer_evidence_v57','predict_candidate_utility_v57',
    'SimilarityTransferMemoryV57','Section Character must match exactly','transfer-only evidence can at most unlock Top2+D',
    'target<-donor','donor_audit_block','transfer_edge_disabled','context_key_v55'
]: assert token in transfer,token

# Cross-character / unrelated dimension transfer must be impossible in code.
assert 'if tc!=dc:return 0.0' in transfer
assert 'if inter<=0 or union<=0:return 0.0' in transfer
assert 'if j<MIN_JACCARD:return 0.0' in transfer
# Transfer-only Top1 is forbidden by local evidence floor.
assert 'local_ev>=HIGH_LOCAL_EVIDENCE_FLOOR' in transfer
assert 'confidence=min(confidence,TRANSFER_CONF_CAP_NO_LOCAL)' in transfer
# Transfer failures calibrate edge memory, not CandidateUtilityMemory.
assert 'def record_audit(self,target,donors,audit_record)' in transfer
assert "e['trust']=max(.15" in transfer
assert 'utility_memory' not in transfer[transfer.index('def record_audit(self,target,donors,audit_record)'):transfer.index('def collect_transfer_evidence_v57')]

# Auto-loop uses transfer predictor before v5.6 audit and calibrates edges from actual audit records.
for token in [
    'SimilarityTransferMemoryV57','predict_candidate_utility_v57','default_transfer_path_v57',
    'transfer_mem=SimilarityTransferMemoryV57','audit_mem.plan(prediction',
    'transfer_mem.record_audit','prediction.transfer_donors','context_similarity_transfer.json',
    'transferred_utility_evidence','transfer_confidence','transfer_detail','--transfer-memory'
]: assert token in loop,token
assert loop.index('predict_candidate_utility_v57(') < loop.index('audit_mem.plan(prediction')
assert loop.index('audit_mem.record_audit(') < loop.index('transfer_mem.record_audit(')

for token in [
    '"context_similarity_transfer"','"same_section_character_only":True','"critic_dimension_overlap_required":True',
    '"min_jaccard":.34','"transfer_only_top1_pruning_forbidden":True',
    '"target_local_evidence_required_for_top1":1.5','AUTO_LOOP_STRINGS_v57.bat'
]: assert token in comp,token

pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)]
seen={}
for n,v in pairs:
    assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc
assert '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0'])
assert 'SonicraftContextSimilarityTransferSmokeV57' in cm

for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1','installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['context_similarity_transfer_v57.py','compile_musicxml_strings_v57.py','auto_loop_strings_v57.py']:
        assert token in text,(rel,token)
collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text();verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v57.bat','AUTO_LOOP_STRINGS_v57.bat']:assert token in collector,token
assert 'Tools/COMPILE_MUSICXML_STRINGS_v57.bat' in verify
assert 'Tools/AUTO_LOOP_STRINGS_v57.bat' in verify
print('SONICRAFT v5.7 Context Similarity Transfer source contract OK')
