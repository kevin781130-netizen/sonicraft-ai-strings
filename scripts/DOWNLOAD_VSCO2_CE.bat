@echo off
setlocal
cd /d "%~dp0.."
set DEST=datasets\raw\VSCO2_CE
if not exist datasets\raw mkdir datasets\raw
if exist "%DEST%\.git" (
  echo [INFO] VSCO 2 CE sparse clone exists. Updating...
  git -C "%DEST%" pull --ff-only
) else (
  git clone --filter=blob:none --no-checkout https://github.com/sgossner/VSCO-2-CE.git "%DEST%"
  if errorlevel 1 goto :fail
  git -C "%DEST%" sparse-checkout init --cone
  git -C "%DEST%" sparse-checkout set Strings
  git -C "%DEST%" checkout master
)
if errorlevel 1 goto :fail
if not exist datasets\manifests mkdir datasets\manifests
if not exist .venv\Scripts\python.exe (
  echo [ERROR] Run scripts\SETUP_TRAINING.bat first.
  goto :fail
)
call .venv\Scripts\activate.bat
python training\scripts\build_vsco_manifest.py --root "%DEST%\Strings" --out datasets\manifests\vsco2_strings.jsonl
if errorlevel 1 goto :fail
(
  echo VSCO 2 Community Edition
  echo Source: https://github.com/sgossner/VSCO-2-CE
  echo Publisher: https://versilian-studios.com/vsco-community/
  echo License: CC0-1.0
  echo Project role: OPTIONAL articulation taxonomy / LIVE-preview experiment only.
  echo IMPORTANT: not ingested by HQ acoustic training by default; viola/cello source layout is section-oriented.
)>"%DEST%\SONICRAFT_SOURCE_TERMS.txt"
echo [OK] VSCO2 CE Strings-only sparse source prepared as OPTIONAL reference.
pause
exit /b 0
:fail
echo [ERROR] VSCO2 CE preparation failed.
pause
exit /b 1
