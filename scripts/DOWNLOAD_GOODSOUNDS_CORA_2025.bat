@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo Run SETUP_TRAINING.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe training\scripts\fetch_goodsounds_cora.py --out data\good_sounds_cora_2025
if errorlevel 1 (
  echo Automatic download did not complete. Open the official DOI only:
  echo https://doi.org/10.34810/DATA2314
  pause
  exit /b 1
)
.venv\Scripts\python.exe training\scripts\build_goodsounds_manifest.py data\good_sounds_cora_2025 --out datasets\manifests\goodsounds_cora_2025.jsonl
pause
