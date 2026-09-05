@echo off
setlocal
cd /d "%~dp0\.."
if "%~1"=="" (
  echo Usage: scripts\BUILD_ROOM_PROFILE_V22.bat ^<folder-with-11-owned-IR-wavs^> [output.json]
  exit /b 2
)
set OUT=%~2
if "%OUT%"=="" set OUT=Room\active_room_profile.json
python training\scripts\build_room_profile_v22.py --ir-dir "%~1" --out "%OUT%" --sample-rate 48000 --taps 64 || exit /b 1
echo [PASS] Room profile: %OUT%
endlocal
