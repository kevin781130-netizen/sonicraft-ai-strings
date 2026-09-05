@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
%PY% "%~dp0runtime\smoke_frontend_v64.py"
if errorlevel 1 pause
