from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
aud=(ROOT/'runtime/counterfactual_auditor_v56.py').read_text()
comp=(ROOT/'runtime/compile_musicxml_strings_v56.py').read_text()
loop=(ROOT/'runtime/auto_loop_strings_v56.py').read_text()
ids=(ROOT/'src/ids.h').read_text();proc=(ROOT/'src/processor.cpp').read_text();ctl=(ROOT/'src/controller.cpp').read_text();cm=(ROOT/'CMakeLists.txt').read_text()

for token in [
    'CounterfactualAuditMemoryV56','AuditPlanV56','BASE_AUDIT_INTERVAL=12',
    'ELEVATED_AUDIT_INTERVAL=6','HIGH_RISK_AUDIT_INTERVAL=4',
    'FALSE_PRUNE_MARGIN=.025','DISABLE_RATE=.25','RECOVERY_CLEAN_AUDITS=4',
    'false_prune_rate_high','counterfactual_gain','recent_false_prune_rate',
    'zero_render_disabled_v54_budget','audit_degraded_confidence_v54_budget',
    'audit_degraded_top2_plus_D','counterfactual_audit_due',
    'aggregate audit outcomes only; no audio/MIDI/score text/file names/identity'
]: assert token in aud,token

assert 'full in pruned and gain>=FALSE_PRUNE_MARGIN' in aud
assert 'ctx["disabled"]=True' in aud
assert 'ctx["disabled"]=False' in aud
assert 'ctx["recent"]=[x for x in ctx.get("recent",[])[-RECOVERY_CLEAN_AUDITS:]' in aud
assert 'audit_slots=[s for s in SLOTS if s not in initial]' in aud

for token in [
    '"counterfactual_render_auditor"','"base_audit_interval":12',
    '"elevated_audit_interval":6','"high_risk_audit_interval":4',
    '"false_prune_margin":.025','"context_disable_rate":.25',
    '"recovery_clean_audits":4','"zero_render_can_be_disabled_per_context":True'
]: assert token in comp,token

for token in [
    'CounterfactualAuditMemoryV56','audit_mem.plan','counterfactual_audit.json',
    'audit_plan.audit_due','candidate_renders_audited','record_audit(',
    'hypothetical_initial_slots','hypothetical_pruned_slots',
    'counterfactual_audit_events','counterfactual_audit_sidecar',
    '--audit-memory','"version":"5.6"'
]: assert token in loop,token

# Scheduled audit happens only after the ordinary v5.5 disagreement/low-margin escalation check.
assert loop.index('should_escalate_v55(') < loop.index('elif audit_plan.audit_due:')
# Audited full evidence remains legal input to v5.5 actual-render-only Utility Memory.
assert 'full_evidence=(len(rendered)==4)' in loop

pairs=[(n,int(v)) for n,v in re.findall(r'(kParam\w+)\s*=\s*(\d+)',ids)];seen={}
for n,v in pairs: assert v not in seen,(v,seen.get(v),n);seen[v]=n
assert max(v for _,v in pairs)==740
assert 'constexpr int kStateVersion = 13;' in proc and '(version<3||version>13)' in ctl
assert any(x in cm for x in ['VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0']) and 'SonicraftCounterfactualAuditorSmokeV56' in cm
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1','installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['counterfactual_auditor_v56.py','compile_musicxml_strings_v56.py','auto_loop_strings_v56.py']: assert token in text,(rel,token)
collector=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text();verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text()
for token in ['COMPILE_MUSICXML_STRINGS_v56.bat','AUTO_LOOP_STRINGS_v56.bat']: assert token in collector,token
assert 'Tools/COMPILE_MUSICXML_STRINGS_v56.bat' in verify and 'Tools/AUTO_LOOP_STRINGS_v56.bat' in verify
print('SONICRAFT v5.6 Counterfactual Render Auditor source contract OK')
