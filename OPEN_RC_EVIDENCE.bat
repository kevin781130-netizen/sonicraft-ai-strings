@echo off
setlocal
cd /d "%~dp0"
if not exist "release\rc_evidence" mkdir "release\rc_evidence"
start "" explorer.exe "%CD%\release\rc_evidence"
endlocal
