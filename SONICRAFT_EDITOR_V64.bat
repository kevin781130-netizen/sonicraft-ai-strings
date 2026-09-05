@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
start "SONICRAFT Editor v6.4" %PY% "%~dp0frontend\editor_server.py" --open
exit /b 0
