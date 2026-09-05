@echo off
setlocal
cd /d "%~dp0\.."
if "%~4"=="" (
 echo Usage: scripts\PROMOTE_NATIVE_RUNTIME_V22.bat ^<footprint.json^> ^<numerical.json^> ^<runtime_abx.json^> ^<acoustic_promotion.json^>
 exit /b 2
)
python training\scripts\build_native_runtime_promotion_v22.py --footprint "%~1" --numerical "%~2" --runtime-abx "%~3" --acoustic-promotion "%~4" --out build\native_runtime_v22\native_runtime_promotion.json || exit /b 1
echo [PASS] ORT runtime has earned promotion. Do not set it default before this evidence exists.
endlocal
