@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title SONICRAFT DNNI - Import Four Timbres

if not exist dnni_input mkdir dnni_input

echo ============================================================
echo DNNI FOUR-TIMBRE IMPORT
echo ============================================================
echo Put exactly four TAR files in:
echo   %CD%\dnni_input
echo.
echo Required order prefixes:
echo   01_name.tar
echo   02_name.tar
echo   03_name.tar
echo   04_name.tar
echo.
echo Slot order maps to timbre_1 ... timbre_4.
echo.

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  echo [ERROR] .venv is not ready.
  echo Run SETUP_DNNI_5090.bat first.
  pause
  exit /b 2
)

python training\scripts\import_dnni_input_dir.py
set "EC=%ERRORLEVEL%"
echo.
if "%EC%"=="0" (
  echo Import/verification finished.
) else (
  echo Import failed. Check filenames and the error above.
  echo Opening dnni_input...
  start "" explorer.exe "%CD%\dnni_input"
)
echo.
pause
exit /b %EC%
