@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

if "%~1"=="" goto :USAGE

"%PY%" "runtime\dnni_model_shell.py" %*
exit /b %ERRORLEVEL%

:USAGE
echo SONICRAFT DNNI Model Shell
echo.
echo Usage:
echo   DNNI_MODEL_SHELL.bat inspect ^<model.dnni^> [--json]
echo   DNNI_MODEL_SHELL.bat scan ^<directory^> [--recursive] [--json]
echo.
echo Recommended private model folder:
echo   models\dnni
echo.
echo Example:
echo   DNNI_MODEL_SHELL.bat scan models\dnni
exit /b 2
