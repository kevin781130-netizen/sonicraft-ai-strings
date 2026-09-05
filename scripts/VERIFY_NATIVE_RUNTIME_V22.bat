@echo off
setlocal
cd /d "%~dp0\.."
if "%~1"=="" ( echo Usage: scripts\VERIFY_NATIVE_RUNTIME_V22.bat ^<native-runtime-bundle-folder^> & exit /b 2 )
python training\scripts\verify_native_runtime_bundle_v22.py --bundle "%~1" --out build\native_runtime_v22\footprint_report.json --max-mib 160 --require-models || exit /b 1
echo [PASS] Native runtime meets the v2.2 no-PyTorch / <=160 MiB footprint contract.
endlocal
