@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
if not defined STAMP set "STAMP=unknown_time"
set "LOG=%ROOT%logs\renderer_%STAMP%.log"
set "EXE=%ROOT%SONICRAFT_AI_Renderer_Service.exe"

>"%LOG%" echo [SONICRAFT DEBUG RENDERER]
>>"%LOG%" echo Time: %DATE% %TIME%
>>"%LOG%" echo Root: %ROOT%
>>"%LOG%" echo CurrentDir: %CD%
>>"%LOG%" echo.

if not exist "%EXE%" (
  echo ERROR: Renderer EXE not found:
  echo   %EXE%
  >>"%LOG%" echo ERROR: Renderer EXE not found: %EXE%
  echo Log: %LOG%
  pause
  exit /b 2
)

echo Launching Renderer Service with console logging...
echo Keep this window open while testing the host/Manager.
echo Log: %LOG%
"%EXE%" >>"%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
>>"%LOG%" echo.
>>"%LOG%" echo ExitCode: %RC%
echo.
echo Renderer exit code: %RC%
echo Log saved to:
echo   %LOG%
pause
exit /b %RC%
