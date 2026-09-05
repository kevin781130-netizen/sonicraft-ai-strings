from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks={
 'VERSION':'5.9.0-soft-archetype-mixture',
 'README.md':'v5.9 — Multi-Archetype Mixture / Soft Classification',
 'START_HERE.txt':'v5.9',
 'START_PREBUILT_RELEASE.txt':'v5.9',
 'manager.ps1':'v5.9 SOFT ARCHETYPE MIXTURE',
 'manager_release.ps1':'v5.9 SOFT ARCHETYPE MIXTURE',
 'installer/inno/SONICRAFT_AI_Strings.iss':'5.9.0-soft-archetype-mixture',
 'installer/BUILD_FINAL_INNO_INSTALLER.ps1':'5.9.0-soft-archetype-mixture',
 'installer/PREBUILT_RELEASE_BUILDER.ps1':'v5.9 SOFT ARCHETYPE MIXTURE',
 'installer/GENERATE_PREBUILT_MANIFEST.ps1':'5.9.0-soft-archetype-mixture',
 'installer/COLLECT_PREBUILT_APP.ps1':'5.9.0-soft-archetype-mixture',
 'scripts/README_MAIN_ENTRYPOINTS.txt':'v5.9 SOFT ARCHETYPE MIXTURE',
}
for rel,token in checks.items():
    text=(ROOT/rel).read_text(errors='ignore')
    if token not in text:
        assert ('v7.0' in text or '7.0.0-rc2' in text or 'v6.4' in text or '6.4.0-frontend-final-candidate' in text or 'v6.2' in text or '6.2.0-acoustic-runtime-provenance' in text or 'v6.1' in text or '6.1.0-reproducible-performance-checkpoint' in text or 'v6.0' in text or '6.0.0-unified-evidence-store' in text),(rel,token)
assert any(x in (ROOT/'CMakeLists.txt').read_text() for x in ['VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0','VERSION 6.2.0','VERSION 6.4.0','VERSION 7.0.0'])
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['archetype_mixture_v59.py','compile_musicxml_strings_v59.py','auto_loop_strings_v59.py']:
        assert token in text,(rel,token)
probe=(ROOT/'installer/INSTALL_AI_RUNTIME_RELEASE.ps1').read_text(errors='ignore')
for token in ['archetype_mixture_v59','compile_musicxml_strings_v59','auto_loop_strings_v59']:
    assert token in probe,token
print('SONICRAFT v5.9 public release/version/installer convergence OK')
