@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  echo Usage: %~nx0 input.wav [output.json]
  exit /b 2
)
set "OUT=%~2"
if "%OUT%"=="" set "OUT=%~dpn1.fcpe.json"
python training\scripts\analyze_with_fcpe.py "%~1" --out "%OUT%"
