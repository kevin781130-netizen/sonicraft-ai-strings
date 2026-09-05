from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks={
 'VERSION':'5.0.0-local-shadow-render-auto-loop',
 'README.md':'v5.0 — Local Shadow Render Auto-Loop',
 'START_HERE.txt':'v5.0',
 'START_PREBUILT_RELEASE.txt':'v5.0',
 'manager.ps1':'v5.0 LOCAL SHADOW RENDER AUTO-LOOP',
 'manager_release.ps1':'v5.0 LOCAL SHADOW RENDER AUTO-LOOP',
 'installer/inno/SONICRAFT_AI_Strings.iss':'5.0.0-local-shadow-render-auto-loop',
 'installer/BUILD_FINAL_INNO_INSTALLER.ps1':'5.0.0-local-shadow-render-auto-loop',
 'installer/PREBUILT_RELEASE_BUILDER.ps1':'v5.0 LOCAL SHADOW RENDER AUTO-LOOP',
 'installer/GENERATE_PREBUILT_MANIFEST.ps1':'5.0.0-local-shadow-render-auto-loop',
 'installer/COLLECT_PREBUILT_APP.ps1':'5.0.0-local-shadow-render-auto-loop',
 'scripts/README_MAIN_ENTRYPOINTS.txt':'v5.0 LOCAL SHADOW RENDER AUTO-LOOP',
}
for rel,token in checks.items():
    text=(ROOT/rel).read_text(errors='ignore')
    if token not in text:
        assert any(x in text for x in ['v7.0','7.0.0-rc2','v6.4','6.4.0-frontend-final-candidate','v6.2','6.2.0-acoustic-runtime-provenance','v6.1','6.1.0-reproducible-performance-checkpoint','v6.0','6.0.0-unified-evidence-store','v5.9','5.9.0-soft-archetype-mixture','v5.8','5.8.0-cross-song-performance-archetype','v5.7','5.7.0-context-similarity-transfer','v5.6','5.6.0-counterfactual-render-auditor','v5.5','5.5.0-candidate-utility-zero-render','v5.4','5.4.0-conductor-steered-candidates','v5.3','5.3.0-long-form-conductor-intent','v5.1','5.1.0-selective-phrase-local-repair','v5.2','5.2.0-global-performance-coherence']),(rel,token)
assert any(x in (ROOT/'CMakeLists.txt').read_text() for x in ['VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0','VERSION 6.2.0','VERSION 6.4.0','VERSION 7.0.0'])
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1','installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['shadow_render_auto_v50.py','compile_musicxml_strings_v50.py','auto_loop_strings_v50.py']:
        assert token in text,(rel,token)
probe=(ROOT/'installer/INSTALL_AI_RUNTIME_RELEASE.ps1').read_text(errors='ignore')
for token in ['shadow_render_auto_v50','compile_musicxml_strings_v50','auto_loop_strings_v50']:
    assert token in probe,token
for tool in ['COMPILE_MUSICXML_STRINGS_v50.bat','AUTO_LOOP_STRINGS_v50.bat']:
    assert tool in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text()
print('SONICRAFT v5.0 public release/version/installer convergence OK')
