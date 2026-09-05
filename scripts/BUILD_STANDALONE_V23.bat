@echo off
setlocal
cd /d "%~dp0\.."
cmake -S . -B build-standalone-v23 -DSONICRAFT_BUILD_VST3=OFF -DSONICRAFT_BUILD_STANDALONE=ON
if errorlevel 1 exit /b %errorlevel%
cmake --build build-standalone-v23 --config Release
if errorlevel 1 exit /b %errorlevel%
echo [PASS] Standalone host built without VST3 SDK.
