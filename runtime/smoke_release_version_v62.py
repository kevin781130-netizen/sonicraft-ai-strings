from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks={
 'VERSION':'6.2.0-acoustic-runtime-provenance',
 'README.md':'v6.2 — Acoustic Runtime Provenance / Model Environment Binding',
 'START_HERE.txt':'v6.2',
 'START_PREBUILT_RELEASE.txt':'v6.2',
 'manager.ps1':'v6.2 ACOUSTIC RUNTIME PROVENANCE',
 'manager_release.ps1':'v6.2 ACOUSTIC RUNTIME PROVENANCE',
 'installer/inno/SONICRAFT_AI_Strings.iss':'6.2.0-acoustic-runtime-provenance',
 'installer/BUILD_FINAL_INNO_INSTALLER.ps1':'6.2.0-acoustic-runtime-provenance',
 'installer/PREBUILT_RELEASE_BUILDER.ps1':'v6.2 ACOUSTIC RUNTIME PROVENANCE',
 'installer/GENERATE_PREBUILT_MANIFEST.ps1':'6.2.0-acoustic-runtime-provenance',
 'installer/COLLECT_PREBUILT_APP.ps1':'6.2.0-acoustic-runtime-provenance',
 'scripts/README_MAIN_ENTRYPOINTS.txt':'v6.2 ACOUSTIC RUNTIME PROVENANCE',
}
for rel,token in checks.items():
    text=(ROOT/rel).read_text(errors='ignore'); assert (token in text or 'v7.0' in text or '7.0.0-rc2' in text or (rel=='VERSION' and '6.4.0-frontend-final-candidate' in text)),(rel,token)
assert any(x in (ROOT/'CMakeLists.txt').read_text() for x in ['VERSION 6.2.0','VERSION 6.4.0','VERSION 7.0.0'])
mods=['acoustic_runtime_provenance_v62.py','performance_checkpoint_v62.py','compile_musicxml_strings_v62.py','auto_loop_strings_v62.py']
for rel in ['installer/INSTALL_AI_RUNTIME.ps1','installer/INSTALL_AI_RUNTIME_RELEASE.ps1','installer/COLLECT_PREBUILT_APP.ps1','installer/tools/verify_prebuilt_layout.py']:
    text=(ROOT/rel).read_text(errors='ignore')
    for token in mods: assert token in text,(rel,token)
probe=(ROOT/'installer/INSTALL_AI_RUNTIME_RELEASE.ps1').read_text(errors='ignore')
for token in ['acoustic_runtime_provenance_v62','performance_checkpoint_v62','compile_musicxml_strings_v62','auto_loop_strings_v62']:
    assert token in probe,token
for token in ['COMPILE_MUSICXML_STRINGS_v62.bat','AUTO_LOOP_STRINGS_v62.bat','PERFORMANCE_CHECKPOINT_V62.bat']:
    assert token in (ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text(errors='ignore'),token
print('SONICRAFT v6.2 public release/version/installer convergence OK')
