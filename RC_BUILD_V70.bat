@echo off
setlocal
cd /d "%~dp0"
if not exist "logs\rc_v70" mkdir "logs\rc_v70"
set "SUMMARY=release\rc_evidence\rc-build-stage.json"
if exist "%SUMMARY%" del /q "%SUMMARY%" >nul 2>&1
echo [SONICRAFT v7.0 RC2] Windows VST3 + Validator + ProductShell build
echo Logs/evidence stay under .\release\rc_evidence and .\logs\rc_v70
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\rc_v70\BUILD_RC_V70.ps1" -ProjectRoot "%CD%" %* 1>"logs\rc_v70\RC_BUILD_V70.log" 2>&1
set EC=%ERRORLEVEL%
if "%EC%"=="0" if not exist "%SUMMARY%" set EC=2
type "logs\rc_v70\RC_BUILD_V70.log"
echo.
if not "%EC%"=="0" echo RC BUILD FAILED. Exit code %EC%. Missing/aborted build evidence also fails closed.
if "%EC%"=="0" echo RC BUILD STAGE PASS. Host/acoustic gates remain separate.
pause
exit /b %EC%
