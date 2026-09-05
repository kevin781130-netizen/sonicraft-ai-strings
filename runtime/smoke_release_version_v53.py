from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks={
 'VERSION':'5.3.0-long-form-conductor-intent',
 'README.md':'v5.3 — Long-Form Conductor Intent / Section Character Lock',
 'START_HERE.txt':'v5.3',
 'START_PREBUILT_RELEASE.txt':'v5.3',
 'manager.ps1':'v5.3 LONG-FORM CONDUCTOR INTENT',
 'manager_release.ps1':'v5.3 LONG-FORM CONDUCTOR INTENT',
 'installer/inno/SONICRAFT_AI_Strings.iss':'5.3.0-long-form-conductor-intent',
 'installer/BUILD_FINAL_INNO_INSTALLER.ps1':'5.3.0-long-form-conductor-intent',
 'installer/PREBUILT_RELEASE_BUILDER.ps1':'v5.3 LONG-FORM CONDUCTOR INTENT',
 'installer/GENERATE_PREBUILT_MANIFEST.ps1':'5.3.0-long-form-conductor-intent',
 'installer/COLLECT_PREBUILT_APP.ps1':'5.3.0-long-form-conductor-intent',
 'scripts/README_MAIN_ENTRYPOINTS.txt':'v5.3 LONG-FORM CONDUCTOR INTENT',
}
for rel,token in checks.items():
    text=(ROOT/rel).read_text(errors='ignore')
    if token not in text:
        assert ('v7.0' in text or '7.0.0-rc2' in text or 'v6.4' in text or '6.4.0-frontend-final-candidate' in text or 'v6.2' in text or '6.2.0-acoustic-runtime-provenance' in text or 'v6.1' in text or '6.1.0-reproducible-performance-checkpoint' in text or 'v6.0' in text or '6.0.0-unified-evidence-store' in text or 'v5.9' in text or '5.9.0-soft-archetype-mixture' in text or 'v5.8' in text or '5.8.0-cross-song-performance-archetype' in text or 'v5.7' in text or '5.7.0-context-similarity-transfer' in text or 'v5.4' in text or '5.4.0-conductor-steered-candidates' in text),(rel,token)
assert any(x in (ROOT/'CMakeLists.txt').read_text() for x in ['VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0','VERSION 6.2.0','VERSION 6.4.0','VERSION 7.0.0'])

for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1',
            'installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in ['conductor_intent_v53.py','compile_musicxml_strings_v53.py','auto_loop_strings_v53.py']:
        assert token in text,(rel,token)

probe=(ROOT/'installer/INSTALL_AI_RUNTIME_RELEASE.ps1').read_text(errors='ignore')
for token in ['conductor_intent_v53','compile_musicxml_strings_v53','auto_loop_strings_v53']:
    assert token in probe,token
print('SONICRAFT v5.3 public release/version/installer convergence OK')
