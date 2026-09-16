@echo off
setlocal
cd /d "%~dp0"
set "MODELROOT=%CD%\release\prebuilt\Models"
set "MANIFEST=%MODELROOT%\release_model_manifest.json"
echo [SONICRAFT v7.0 RC] FINAL MODEL PROVENANCE GATE
python "%CD%\training\final_model_manifest_gate_v70.py" "%MANIFEST%" --model-root "%MODELROOT%"
exit /b %ERRORLEVEL%
