@echo off
setlocal
cd /d "%~dp0\.."
if "%~1"=="" (echo Usage: VERIFY_NATIVE_RUNTIME_V23.bat ^<bundle-dir^> & exit /b 2)
python training\scripts\verify_native_runtime_bundle_v23.py --bundle "%~1" --out "%~1\footprint_v23.json" --deployment-kind embedded-python-ort
