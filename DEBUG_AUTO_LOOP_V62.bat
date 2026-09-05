@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
if not defined STAMP set "STAMP=unknown_time"
set "LOG=%ROOT%logs\auto_loop_v62_%STAMP%.log"

if "%~1"=="" (
  echo Drag a MusicXML / XML / MXL score onto DEBUG_AUTO_LOOP_V62.bat
  echo.
  echo This debug launcher keeps the console open and writes a full log under:
  echo   %ROOT%logs
  pause
  exit /b 2
)

>"%LOG%" echo [SONICRAFT DEBUG AUTO LOOP v6.2]
>>"%LOG%" echo Time: %DATE% %TIME%
>>"%LOG%" echo Root: %ROOT%
>>"%LOG%" echo Score: %~f1
>>"%LOG%" echo CurrentDir: %CD%
>>"%LOG%" echo.
>>"%LOG%" echo [where python]
where python >>"%LOG%" 2>&1
>>"%LOG%" echo.
>>"%LOG%" echo [python version]
python --version >>"%LOG%" 2>&1
>>"%LOG%" echo.
>>"%LOG%" echo [run]

echo Running v6.2 Auto-Loop in debug mode...
echo Log: %LOG%
python -X faulthandler "%ROOT%runtime\auto_loop_strings_v62.py" "%~f1" >>"%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
>>"%LOG%" echo.
>>"%LOG%" echo ExitCode: %RC%
echo.
echo Auto-Loop exit code: %RC%
echo Log saved to:
echo   %LOG%
pause
exit /b %RC%
