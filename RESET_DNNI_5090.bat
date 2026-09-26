@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title SONICRAFT DNNI - Archive and Reset Training State

echo ============================================================
echo ARCHIVE / RESET DNNI TRAINING STATE
echo ============================================================
echo.
echo This will MOVE old DNNI checkpoints and latent files into:
echo   archive\dnni5090\YYYYMMDD_HHMMSS
echo.
echo It will NOT touch:
echo   dnni_input\
echo   datasets\dnni_four_timbres\source\
echo   datasets\dnni_four_timbres\rendered\*.wav
echo.
choice /c YN /n /m "Archive current training state and reset? [Y/N]: "
if errorlevel 2 exit /b 0

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  echo [ERROR] .venv is not ready. Run SETUP_DNNI_5090.bat first.
  pause
  exit /b 2
)

python training\scripts\archive_dnni_training_state.py --include-logs
set "EC=%ERRORLEVEL%"
echo.
if "%EC%"=="0" (
  echo [DONE] Old training outputs were archived.
  echo You can now start TRAIN_DNNI_5090.bat against the current data fingerprint.
) else (
  echo [ERROR] Archive/reset failed. Nothing else was intentionally deleted.
)
echo.
pause
exit /b %EC%
