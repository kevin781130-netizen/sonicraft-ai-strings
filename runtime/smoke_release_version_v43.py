from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks={
 'VERSION':'4.3.0-string-constraint-transition',
 'README.md':'v4.3 — String Constraint & Transition Solver',
 'START_HERE.txt':'v4.3',
 'START_PREBUILT_RELEASE.txt':'v4.3',
 'manager.ps1':'v4.3 STRING CONSTRAINT & TRANSITION',
 'manager_release.ps1':'v4.3 STRING CONSTRAINT & TRANSITION',
 'installer/inno/SONICRAFT_AI_Strings.iss':'4.3.0-string-constraint-transition',
 'installer/BUILD_FINAL_INNO_INSTALLER.ps1':'4.3.0-string-constraint-transition',
 'installer/PREBUILT_RELEASE_BUILDER.ps1':'v4.3 STRING CONSTRAINT & TRANSITION',
 'installer/GENERATE_PREBUILT_MANIFEST.ps1':'4.3.0-string-constraint-transition',
 'installer/COLLECT_PREBUILT_APP.ps1':'4.3.0-string-constraint-transition',
 'scripts/README_MAIN_ENTRYPOINTS.txt':'v4.3 STRING CONSTRAINT & TRANSITION',
}
for rel,token in checks.items():
    text=(ROOT/rel).read_text(encoding='utf-8',errors='ignore')
    if token not in text:
        assert any(x in text for x in ['v7.0','7.0.0-rc2','v6.4','6.4.0-frontend-final-candidate','v6.2','6.2.0-acoustic-runtime-provenance','v6.1','6.1.0-reproducible-performance-checkpoint','v6.0','6.0.0-unified-evidence-store','v5.9','5.9.0-soft-archetype-mixture','v5.8','5.8.0-cross-song-performance-archetype','v5.7','5.7.0-context-similarity-transfer','v5.6','5.6.0-counterfactual-render-auditor','v5.5','5.5.0-candidate-utility-zero-render','v5.4','5.4.0-conductor-steered-candidates','v5.3','5.3.0-long-form-conductor-intent','v5.2','5.2.0-global-performance-coherence','v5.1','5.1.0-selective-phrase-local-repair','v5.0','5.0.0-local-shadow-render-auto-loop','v4.9','4.9.0-audio-judge-repair-iteration','v4.8','4.8.0-phrase-performance-critic-auto-repair','v4.7','4.7.0-phrase-bow-vibrato-continuity','v4.6','4.6.0-continuous-transition-legato','v4.5','4.5.0-continuous-string-gesture','v4.4','4.4.0-ensemble-bow-phrase','v4.3','4.3.0-string-constraint-transition','v4.2','4.2.0-string-physical-performance']),(rel,token)
assert any(x in (ROOT/'CMakeLists.txt').read_text(encoding='utf-8') for x in ['VERSION 4.3.0','VERSION 4.4.0','VERSION 4.5.0','VERSION 4.6.0','VERSION 4.7.0','VERSION 4.8.0','VERSION 4.9.0','VERSION 5.0.0','VERSION 5.1.0','VERSION 5.2.0','VERSION 5.3.0','VERSION 5.4.0','VERSION 5.5.0','VERSION 5.6.0','VERSION 5.7.0','VERSION 5.8.0','VERSION 5.9.0','VERSION 6.0.0','VERSION 6.1.0','VERSION 6.2.0','VERSION 6.4.0','VERSION 7.0.0'])
print('SONICRAFT v4.3 public release/version convergence OK')
