@echo off
setlocal
cd /d "%~dp0"
set "ROOT=%CD%\"
set "PY=python"
if exist "%ROOT%runtime\venv\Scripts\python.exe" set "PY=%ROOT%runtime\venv\Scripts\python.exe"
if exist "%ROOT%Runtime\venv\Scripts\python.exe" set "PY=%ROOT%Runtime\venv\Scripts\python.exe"
echo [SONICRAFT v7.0 RC] RELEASE EVIDENCE STATUS
"%PY%" "%ROOT%scripts\release_evidence_status_v70.py" --root "%ROOT%" %*
set EC=%ERRORLEVEL%
pause
exit /b %EC%
