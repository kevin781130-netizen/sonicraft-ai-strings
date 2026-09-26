@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title SONICRAFT DNNI - Stage Reset

echo ============================================================
echo DNNI STAGE RESET (ARCHIVE FIRST, NEVER DELETE SOURCE DATA)
echo ============================================================
echo.
echo   [1] Codec + Latents + Renderer + Distill + Shortcut
echo   [2] Renderer + Distill + Shortcut
echo   [3] Distill + Shortcut
echo   [4] Shortcut only
echo   [Q] Cancel
echo.
choice /c 1234Q /n /m "Reset from which stage? "
if errorlevel 5 exit /b 0
if errorlevel 4 set "STAGE=shortcut"
if errorlevel 3 set "STAGE=distill"
if errorlevel 2 set "STAGE=renderer"
if errorlevel 1 set "STAGE=codec"

echo.
echo Selected: %STAGE%
choice /c YN /n /m "Archive this stage and everything after it? [Y/N]: "
if errorlevel 2 exit /b 0

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  echo [ERROR] .venv is not ready. Run SETUP_DNNI_5090.bat first.
  pause
  exit /b 2
)

python training\scripts\archive_dnni_training_state.py --from-stage "%STAGE%" --include-logs
set "EC=%ERRORLEVEL%"
echo.
if "%EC%"=="0" (
  echo [DONE] Stage reset archived safely.
  echo Start TRAIN_DNNI_5090.bat again when ready.
) else (
  echo [ERROR] Stage reset failed. No source DNNI/WAV data was intentionally deleted.
)
echo.
pause
exit /b %EC%
