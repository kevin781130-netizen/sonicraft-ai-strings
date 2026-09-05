from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
assert (ROOT/'VERSION').read_text().strip()=='7.0.0-rc2'
assert 'VERSION 7.0.0' in (ROOT/'CMakeLists.txt').read_text(errors='ignore')
for rel,token in {
 'START_HERE.txt':'v7.0 RC2',
 'START_PREBUILT_RELEASE.txt':'v7.0 RC2',
 'release/README.txt':'v7.0 RC2',
 'docs/RC_GATE_V7.0.md':'Fail-closed final gate',
 'installer/build_release_windows.ps1':'9fad9770f2ae8542ab1a548a68c1ad1ac690abe0',
 'installer/BUILD_FINAL_INNO_INSTALLER.ps1':"7.0.0-rc2",
 'installer/GENERATE_PREBUILT_MANIFEST.ps1':"7.0.0-rc2",
 'installer/inno/SONICRAFT_AI_Strings.iss':'7.0.0-rc2',
 'RC_BUILD_V70.bat':'BUILD_RC_V70.ps1',
 'QA_CUBASE_V70.bat':'Cubase',
 'QA_STUDIO_ONE_V70.bat':'StudioOne',
 'QA_RTX5090_ACOUSTIC_V70.bat':'RUN_ACOUSTIC_QA_V70.ps1',
 'FINAL_GATE_V70.bat':'FINAL_GATE_V70.ps1',
}.items():
    text=(ROOT/rel).read_text(errors='ignore');assert token in text,(rel,token)
f=json.loads((ROOT/'release/frontier_status_v7.0.json').read_text())
assert f['feature_freeze'] is True
assert f['commercial_binary_approved'] is False
assert f['pinned_dependencies']['steinberg_vst3_sdk']['version']=='3.8.0'
assert f['pinned_dependencies']['steinberg_vst3_sdk']['commit']=='9fad9770f2ae8542ab1a548a68c1ad1ac690abe0'
print('SONICRAFT v7.0 RC release/version/gate convergence OK')
