@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
if exist "%~dp0runtime\venv\Scripts\python.exe" set "PY=%~dp0runtime\venv\Scripts\python.exe"
if exist "%~dp0..\Runtime\venv\Scripts\python.exe" set "PY=%~dp0..\Runtime\venv\Scripts\python.exe"
%PY% "%~dp0runtime\frontend_layout_gate_v70.py"
if errorlevel 1 pause
