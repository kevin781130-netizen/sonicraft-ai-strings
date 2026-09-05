@echo off
setlocal
cd /d "%~dp0\.."
if "%~1"=="" (
  echo Usage: %~nx0 path\to\rights_cleared_manifest.jsonl [output.jsonl]
  exit /b 2
)
set OUT=%~2
if "%OUT%"=="" set OUT=datasets\processed\vibrato_analysis\enriched_manifest.jsonl
call .venv\Scripts\activate.bat 2>nul
python training\scripts\analyze_vibrato_rights_cleared.py --manifest "%~1" --out "%OUT%" --registry training\dataset_registry.json
endlocal
