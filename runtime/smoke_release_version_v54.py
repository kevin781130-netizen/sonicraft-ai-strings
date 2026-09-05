from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks={
 'VERSION':'5.4.0-conductor-steered-candidates',
 'README.md':'v5.4 — Conductor-Steered Candidate Generation',
 'START_HERE.txt':'v5.4',
 'START_PREBUILT_RELEASE.txt':'v5.4',
 'manager.ps1':'v5.4 CONDUCTOR-STEERED CANDIDATES',
 'manager_release.ps1':'v5.4 CONDUCTOR-STEERED CANDIDATES',
 'installer/inno/SONICRAFT_AI_Strings.iss':'5.4.0-conductor-steered-candidates',
 'installer/BUILD_FINAL_INNO_INSTALLER.ps1':'5.4.0-conductor-steered-candidates',
 'installer/PREBUILT_RELEASE_BUILDER.ps1':'v5.4 CONDUCTOR-STEERED CANDIDATES',
 'installer/GENERATE_PREBUILT_MANIFEST.ps1':'5.4.0-conductor-steered-candidates',
 'installer/COLLECT_PREBUILT_APP.ps1':'5.4.0-conductor-steered-candidates',
 'scripts/README_MAIN_ENTRYPOINTS.txt':'v5.4 CONDUCTOR-STEERED CANDIDATES',
}
for rel,token in checks.items():
    text=(ROOT/rel).read_text(errors='ignore')
    if token not in text:
        assert ('v7.0' in text or '7.0.0-rc2' in text or 'v6.4' in text or '6.4.0-frontend-final-candidate' in text or 'v6.2' in text or '6.2.0-acoustic-runtime-provenance' in text or 'v6.1' in text or '6.1.0-reproducible-performance-checkpoint' in text or 'v6.0' in text or '6.0.0-unified-evidence-store' in text or 'v5.9' in text or '5.9.0-soft-archetype-mixture' in text or 'v5.8' in text or '5.8.0-cross-song-performance-archetype' in text or 'v5.7' in text or '5.7.0-context-similarity-transfer' in text or 'v5.6' in text or '5.6.0-counterfactual-render-auditor' in text or 'v5.5' in text or '5.5.0-candidate-utility-zero-render' in text),(rel,token)
assert any(x in (ROOT/'CMakeLists.txt').read_text() for x in ['VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0','VERSION 6.2.0','VERSION 6.4.0','VERSION 7.0.0'])
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['conductor_candidate_steering_v54.py','compile_musicxml_strings_v54.py','auto_loop_strings_v54.py']:
        assert token in text,(rel,token)
probe=(ROOT/'installer/INSTALL_AI_RUNTIME_RELEASE.ps1').read_text(errors='ignore')
for token in ['conductor_candidate_steering_v54','compile_musicxml_strings_v54','auto_loop_strings_v54']:
    assert token in probe,token
print('SONICRAFT v5.4 public release/version/installer convergence OK')
