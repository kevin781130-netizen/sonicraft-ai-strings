@echo off
setlocal
cd /d "%~dp0"
title SONICRAFT DNNI RTX 5090 - Training Status
call .venv\Scripts\activate.bat 2>nul
echo.
python training\scripts\dnni_training_status.py
set "EC=%ERRORLEVEL%"
echo.
if "%EC%"=="0" (
  echo Checkpoints look healthy.
) else (
  echo One or more checkpoints need attention before automatic resume.
)
echo.
pause
exit /b %EC%
