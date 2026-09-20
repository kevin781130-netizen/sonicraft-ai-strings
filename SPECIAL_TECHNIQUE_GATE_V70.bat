@echo off
setlocal
set "ROOT=%~dp0"
python "%ROOT%scripts\special_technique_gate_v70.py"
exit /b %ERRORLEVEL%
