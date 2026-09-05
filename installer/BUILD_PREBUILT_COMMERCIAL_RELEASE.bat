@echo off
setlocal
cd /d "%~dp0.."
echo SONICRAFT AI Strings - Prebuilt Commercial Release Builder
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\PREBUILT_RELEASE_BUILDER.ps1" -ProjectRoot "%CD%" -BuildInstaller
if errorlevel 1 (
  echo.
  echo RELEASE BUILD FAILED. No customer installer was produced.
  pause
  exit /b 1
)
echo.
echo DONE. Open release\final for the real prebuilt installer.
pause
