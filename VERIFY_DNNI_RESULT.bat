@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title SONICRAFT DNNI - Verify Final Training Result

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  echo [ERROR] .venv is not ready. Run SETUP_DNNI_5090.bat first.
  pause
  exit /b 2
)

python training\scripts\dnni_training_finalize.py --verify
set "EC=%ERRORLEVEL%"
echo.
if "%EC%"=="0" (
  echo Final DNNI research checkpoint integrity is valid.
) else (
  echo Verification failed. Do not use/copy the final checkpoint until resolved.
)
echo.
pause
exit /b %EC%
