@echo off
setlocal
cd /d "%~dp0.."
echo [SONICRAFT] Building Windows x64 VST3 + VSTGUI release...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\build_release_windows.ps1" -ProjectRoot "%CD%"
if errorlevel 1 (
  echo.
  echo Build failed. See build_release_windows.log
  exit /b 1
)
echo.
echo Release bundle is under .\release\SONICRAFT AI Strings Q4.vst3
endlocal
