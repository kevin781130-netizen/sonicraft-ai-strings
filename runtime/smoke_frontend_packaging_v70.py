from __future__ import annotations
import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)

def main() -> int:
    collect=(ROOT/'installer/COLLECT_PREBUILT_APP.ps1').read_text(encoding='utf-8', errors='ignore')
    for token in [
        "Frontend\\index.html",
        "Frontend\\editor_server.py",
        "Tools\\OPEN_INSTRUMENT_EDITOR.bat",
        "COMPILE_MUSICXML_STRINGS_v62.bat",
        "AUTO_LOOP_STRINGS_v62.bat",
        "PERFORMANCE_CHECKPOINT_V62.bat",
    ]:
        require(token in collect, f'prebuilt collector missing {token}')

    verify=(ROOT/'installer/tools/verify_prebuilt_layout.py').read_text(encoding='utf-8', errors='ignore')
    for token in ['Frontend/index.html','Frontend/editor_server.py','Tools/OPEN_INSTRUMENT_EDITOR.bat']:
        require(token in verify, f'prebuilt verifier missing {token}')

    mgr=(ROOT/'manager_release.ps1').read_text(encoding='utf-8', errors='ignore')
    require('OPEN_INSTRUMENT_EDITOR.bat' in mgr, 'manager has no Instrument Editor launcher')
    require('Open Instrument Editor' in mgr, 'manager UI has no Instrument Editor button')

    for rel in ['COMPILE_MUSICXML_STRINGS_v62.bat','AUTO_LOOP_STRINGS_v62.bat','PERFORMANCE_CHECKPOINT_V62.bat']:
        text=(ROOT/rel).read_text(encoding='utf-8-sig', errors='ignore')
        require('%ROOT%..\\Runtime\\' in text, f'{rel} lacks installed-layout Runtime fallback')
        require('runtime\\venv\\Scripts\\python.exe' in text, f'{rel} lacks installed runtime Python selection')

    # Import an exact copy from a simulated installed App/Frontend path and prove
    # resolve_bat() selects App/Tools instead of assuming the source-tree root.
    with tempfile.TemporaryDirectory(prefix='sonicraft_v70_frontend_') as td:
        app=Path(td)/'App'; front=app/'Frontend'; tools=app/'Tools'
        front.mkdir(parents=True); tools.mkdir(parents=True)
        shutil.copy2(ROOT/'frontend/editor_server.py', front/'editor_server.py')
        shutil.copy2(ROOT/'frontend/index.html', front/'index.html')
        dummy=tools/'COMPILE_MUSICXML_STRINGS_v62.bat'; dummy.write_text('@echo off\nexit /b 0\n', encoding='utf-8')
        spec=importlib.util.spec_from_file_location('sonicraft_installed_editor_smoke', front/'editor_server.py')
        require(spec is not None and spec.loader is not None, 'cannot import installed editor copy')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        resolved=mod.resolve_bat('COMPILE_MUSICXML_STRINGS_v62.bat')
        require(resolved.resolve()==dummy.resolve(), f'installed editor resolved wrong BAT: {resolved}')

    print('SONICRAFT v7.0 frontend consumer-packaging smoke PASS')
    print(' Frontend payload included: PASS')
    print(' Manager -> Instrument Editor entry: PASS')
    print(' Installed App/Tools BAT resolution: PASS')
    print(' Source/installed dual-layout v6.2 BATs: PASS')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
