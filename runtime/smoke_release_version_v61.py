from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks={
 'VERSION':'6.1.0-reproducible-performance-checkpoint',
 'README.md':'v6.1 — Reproducible Performance Checkpoint / Policy–Evidence Binding',
 'START_HERE.txt':'v6.1',
 'START_PREBUILT_RELEASE.txt':'v6.1',
 'manager.ps1':'v6.1 REPRODUCIBLE PERFORMANCE CHECKPOINT',
 'manager_release.ps1':'v6.1 REPRODUCIBLE PERFORMANCE CHECKPOINT',
 'installer/inno/SONICRAFT_AI_Strings.iss':'6.1.0-reproducible-performance-checkpoint',
 'installer/BUILD_FINAL_INNO_INSTALLER.ps1':'6.1.0-reproducible-performance-checkpoint',
 'installer/PREBUILT_RELEASE_BUILDER.ps1':'v6.1 REPRODUCIBLE PERFORMANCE CHECKPOINT',
 'installer/GENERATE_PREBUILT_MANIFEST.ps1':'6.1.0-reproducible-performance-checkpoint',
 'installer/COLLECT_PREBUILT_APP.ps1':'6.1.0-reproducible-performance-checkpoint',
 'scripts/README_MAIN_ENTRYPOINTS.txt':'v6.1 REPRODUCIBLE PERFORMANCE CHECKPOINT',
}
for rel,token in checks.items():
    text=(ROOT/rel).read_text(errors='ignore');
    if token not in text: assert ('v7.0' in text or '7.0.0-rc2' in text or 'v6.4' in text or '6.4.0-frontend-final-candidate' in text or 'v6.2' in text or '6.2.0-acoustic-runtime-provenance' in text),(rel,token)
assert any(x in (ROOT/'CMakeLists.txt').read_text() for x in ['VERSION 6.1.0','VERSION 6.2.0','VERSION 6.4.0','VERSION 7.0.0'])
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['performance_checkpoint_v61.py','compile_musicxml_strings_v61.py','auto_loop_strings_v61.py']:
        assert token in text,(rel,token)
probe=(ROOT/'installer/INSTALL_AI_RUNTIME_RELEASE.ps1').read_text(errors='ignore')
for token in ['performance_checkpoint_v61','compile_musicxml_strings_v61','auto_loop_strings_v61']:
    assert token in probe,token
print('SONICRAFT v6.1 public release/version/installer convergence OK')
