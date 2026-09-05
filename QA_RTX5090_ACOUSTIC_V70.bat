@echo off
setlocal
cd /d "%~dp0"
echo SONICRAFT v7.0 RTX 5090 / Model Acoustic Gate
echo.
echo Optional advanced use:
echo   QA_RTX5090_ACOUSTIC_V70.bat -ModelDir "D:\Models" -Checkpoint "D:\qa\checkpoint.json" -Score "D:\qa\score.musicxml" -Store "D:\qa\evidence_store.json"
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\rc_v70\RUN_ACOUSTIC_QA_V70.ps1" -ProjectRoot "%CD%" %*
set EC=%ERRORLEVEL%
pause
exit /b %EC%
