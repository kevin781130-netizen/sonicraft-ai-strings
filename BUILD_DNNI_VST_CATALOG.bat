@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
"%PY%" "runtime\build_dnni_vst_catalog.py" %*
exit /b %ERRORLEVEL%
