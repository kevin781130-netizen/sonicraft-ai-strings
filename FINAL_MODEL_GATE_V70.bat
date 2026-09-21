@echo off
setlocal
cd /d "%~dp0"
set "ROOT=%CD%\"
set "PY=python"
if exist "%ROOT%runtime\venv\Scripts\python.exe" set "PY=%ROOT%runtime\venv\Scripts\python.exe"
if exist "%ROOT%Runtime\venv\Scripts\python.exe" set "PY=%ROOT%Runtime\venv\Scripts\python.exe"
set "MODELROOT=%ROOT%release\prebuilt\Models"
set "MANIFEST=%MODELROOT%\release_model_manifest.json"
echo [SONICRAFT v7.0 RC] FINAL MODEL PROVENANCE GATE
"%PY%" "%ROOT%training\final_model_manifest_gate_v70.py" "%MANIFEST%" --model-root "%MODELROOT%"
exit /b %ERRORLEVEL%
