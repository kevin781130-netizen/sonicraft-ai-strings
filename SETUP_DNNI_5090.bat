@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title SONICRAFT DNNI RTX 5090 - Environment Setup

echo ============================================================
echo SONICRAFT AI Strings - RTX 5090 Training Environment
echo ============================================================
echo.
echo Recommended path: Python 3.11 + PyTorch 2.12 + CUDA 13.0 wheel.
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python launcher "py" was not found.
  echo Install Python 3.11 x64, then run this BAT again.
  pause
  exit /b 2
)

if not exist .venv (
  echo [1/5] Creating Python 3.11 virtual environment...
  py -3.11 -m venv .venv || goto :FAIL
) else (
  echo [1/5] Existing .venv found.
)

call .venv\Scripts\activate.bat || goto :FAIL

echo [2/5] Updating pip...
python -m pip install --upgrade pip setuptools wheel || goto :FAIL

echo [3/5] Installing Blackwell-capable PyTorch CUDA 13.0...
python -m pip install --upgrade torch==2.12.0 torchaudio==2.12.0 --index-url https://download.pytorch.org/whl/cu130 || goto :FAIL

echo [4/5] Installing SONICRAFT training dependencies...
python -m pip install -r training\requirements.txt --upgrade-strategy only-if-needed || goto :FAIL

echo [5/5] RTX 5090 preflight...
python training\scripts\dnni_5090_preflight.py || goto :FAIL

echo.
echo ============================================================
echo [DONE] RTX 5090 training environment is ready.
echo Next: double-click DNNI_5090_MANAGER.bat
echo ============================================================
pause
exit /b 0

:FAIL
set "EC=%ERRORLEVEL%"
if "%EC%"=="0" set "EC=1"
echo.
echo ============================================================
echo [SETUP FAILED] code=%EC%
echo Review the error above. Existing .venv files were not deleted.
echo ============================================================
pause
exit /b %EC%
