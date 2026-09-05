from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def need(rel, token=None):
    p=ROOT/rel
    if not p.is_file(): errors.append(f'missing {rel}'); return ''
    t=p.read_text(encoding='utf-8',errors='ignore')
    if token is not None and token not in t: errors.append(f'{rel}: missing token {token!r}')
    return t

if (ROOT/'VERSION').read_text().strip()!='7.0.0-rc2': errors.append('VERSION is not 7.0.0-rc2')
need('CMakeLists.txt','project(SonicraftAIStringsQ4 VERSION 7.0.0')
build=need('installer/build_release_windows.ps1','9fad9770f2ae8542ab1a548a68c1ad1ac690abe0')
for token in ['checkout','--detach','submodule','validator-pass.json','build-provenance.json']:
    if token not in build: errors.append(f'Windows builder missing reproducibility token: {token}')
if re.search(r'git\s+clone[^\n]+vst3sdk[^\n]+(?:master|main)',build,re.I): errors.append('Windows builder still clones moving VST3 branch explicitly')
for rel in [
 'installer/rc_v70/BUILD_RC_V70.ps1','installer/rc_v70/RUN_HOST_QA_V70.ps1',
 'installer/rc_v70/RUN_ACOUSTIC_QA_V70.ps1','installer/rc_v70/FINAL_GATE_V70.ps1',
 'RC_BUILD_V70.bat','QA_CUBASE_V70.bat','QA_STUDIO_ONE_V70.bat','QA_RTX5090_ACOUSTIC_V70.bat','FINAL_GATE_V70.bat']:
    need(rel)
need('installer/inno/SONICRAFT_AI_Strings.iss','#define AppVersion "7.0.0-rc2"')
need('installer/BUILD_FINAL_INNO_INSTALLER.ps1',"[string]$Version='7.0.0-rc2'")
need('installer/GENERATE_PREBUILT_MANIFEST.ps1',"version='7.0.0-rc2'")
need('resource/SONICRAFT_AI_Strings_Q4.uidesc','tag="828"')

collect=need('installer/COLLECT_PREBUILT_APP.ps1','Frontend\\editor_server.py')
for token in ['Frontend\\index.html','Tools\\OPEN_INSTRUMENT_EDITOR.bat','COMPILE_MUSICXML_STRINGS_v62.bat','AUTO_LOOP_STRINGS_v62.bat','PERFORMANCE_CHECKPOINT_V62.bat']:
    if token not in collect: errors.append(f'prebuilt collector missing frontend/runtime token: {token}')
need('installer/tools/verify_prebuilt_layout.py','Frontend/index.html')
need('manager_release.ps1','OPEN_INSTRUMENT_EDITOR.bat')
for rel in ['COMPILE_MUSICXML_STRINGS_v62.bat','AUTO_LOOP_STRINGS_v62.bat','PERFORMANCE_CHECKPOINT_V62.bat']:
    bt=need(rel,'%ROOT%..\\Runtime\\')
    if 'runtime\\venv\\Scripts\\python.exe' not in bt: errors.append(f'{rel}: installed runtime Python fallback missing')
need('runtime/smoke_frontend_packaging_v70.py','consumer-packaging smoke PASS')
need('FRONTEND_LAYOUT_GATE_V70.bat','frontend_layout_gate_v70.py')
layout_gate=ROOT/'runtime'/'frontend_layout_gate_v70.py'
if not layout_gate.is_file():
    errors.append('missing runtime/frontend_layout_gate_v70.py')
else:
    cp=subprocess.run([sys.executable,str(layout_gate)],cwd=str(ROOT),capture_output=True,text=True)
    if cp.returncode!=0:
        errors.append('frontend layout gate failed: '+((cp.stdout+'\n'+cp.stderr).strip()[-3000:]))

gate=need('runtime/release_gate_v70.py','acoustic evidence is not bound to a model manifest hash')
for token in ['host_exe_sha256','expected_sdk','9fad9770f2ae8542ab1a548a68c1ad1ac690abe0']:
    if token not in gate: errors.append(f'final gate missing provenance token: {token}')
need('installer/rc_v70/RUN_ACOUSTIC_QA_V70.ps1','model_manifest_sha256')
need('installer/rc_v70/RUN_HOST_QA_V70.ps1','host_exe_sha256')
runtime_install=need('installer/INSTALL_AI_RUNTIME_RELEASE.ps1','Python.Python.3.11')
for token in ['onnxruntime==1.29.0','torch==2.8.0','not(Compatible-Python $VenvPy)']:
    if token not in runtime_install: errors.append(f'release runtime installer missing compatibility token: {token}')
if 'Python.Python.3.10' in runtime_install or 'Python310' in runtime_install: errors.append('release runtime installer still targets incompatible Python 3.10')
need('runtime/smoke_runtime_installer_contract_v70.py','runtime installer compatibility contract PASS')
front=ROOT/'release/frontier_status_v7.0.json'
if front.exists():
    try:
        d=json.loads(front.read_text(encoding='utf-8'))
        if d.get('commercial_binary_approved') is True: errors.append('frontier_status_v7.0 incorrectly claims commercial approval before host/acoustic gates')
    except Exception as e: errors.append(f'invalid frontier_status_v7.0.json: {e}')
else: errors.append('missing release/frontier_status_v7.0.json')
if errors:
    print('SONICRAFT v7.0 RC SOURCE GATE: BLOCKED')
    for e in errors: print(' -',e)
    raise SystemExit(2)
print('SONICRAFT v7.0 RC SOURCE GATE: PASS')
print(' Frontend layout/source lock: PASS')
print(' Pinned VST3 SDK 3.8.0 commit contract: PASS')
print(' Fail-closed Validator/Host/Acoustic gate harness: PASS')
print(' Commercial binary approval remains FALSE until Windows evidence exists.')
