@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "%~dp0logs\frontend_v64" mkdir "%~dp0logs\frontend_v64"
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set "D=%%a-%%b-%%c"
set "LOG=%~dp0logs\frontend_v64\editor_debug.log"
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
echo ============================================================ >> "%LOG%"
echo [%date% %time%] SONICRAFT Editor v6.4 Debug >> "%LOG%"
echo ROOT=%~dp0 >> "%LOG%"
%PY% --version >> "%LOG%" 2>&1
%PY% "%~dp0frontend\editor_server.py" --open --verbose 1>>"%LOG%" 2>&1
set "RC=%errorlevel%"
echo EXIT=%RC% >> "%LOG%"
echo.
echo Editor stopped with exit code %RC%.
echo Log: "%LOG%"
pause
exit /b %RC%
